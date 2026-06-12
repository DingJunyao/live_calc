from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_, text
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.merchant import Merchant, FavoriteMerchant
from app.models.map_config import MapConfiguration
from app.schemas.merchant import (
    MerchantCreate,
    MerchantUpdate,
    MerchantResponse,
    FavoriteMerchantCreate,
    FavoriteMerchantResponse,
    RouteCalculateRequest,
    RouteCalculateResponse
)
from app.schemas.common import PaginatedResponse
from app.services.map_service import calculate_route
from app.models.product import ProductRecord
from app.models.product_entity import Product
from app.models.unit import Unit
from app.schemas.product import ProductRecordResponse

from datetime import datetime as _dt
from app.utils.datetime_utils import serialize_datetime

# SQLite 时间字符串格式（UTC naive）：'2026-06-11 03:38:00.000000'
_SQLITE_TS_FMTS = [
    '%Y-%m-%d %H:%M:%S.%f',
    '%Y-%m-%d %H:%M:%S',
]


def _to_iso(value) -> str | None:
    """安全转带时区的 ISO 字符串。

    兼容：
    - datetime 对象 → 直接用 serialize_datetime 加 +00:00
    - SQLite TEXT 时间字符串（naive UTC） → 解析后加 +00:00
    - 其他字符串 → 透传
    """
    if not value:
        return None
    if isinstance(value, _dt):
        return serialize_datetime(value)
    if isinstance(value, str):
        for fmt in _SQLITE_TS_FMTS:
            try:
                dt = _dt.strptime(value, fmt)
                return serialize_datetime(dt)
            except ValueError:
                continue
        # 已经是 ISO 格式或无法识别的字符串，原样返回
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


router = APIRouter()


@router.get("/map-config")
async def get_public_map_config(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取公开的地图配置 - 任何登录用户都可以访问"""
    try:
        config = db.query(MapConfiguration).first()
        if not config:
            # 如果没有配置，返回默认配置
            return {
                "available_maps": ["amap", "baidu", "tencent", "tianditu", "osm"],
                "default_map": "amap",
                "map_api_keys": {
                    "amap": None,
                    "amap_security": None,
                    "baidu": None,
                    "tencent": None,
                    "tianditu": {"token": "", "type": "vec"}
                }
            }
        return config.to_dict()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取地图配置时发生错误: {str(e)}"
        )


@router.post("", response_model=MerchantResponse)
async def create_merchant(
    merchant: MerchantCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建商家"""
    try:
        db_merchant = Merchant(
            user_id=current_user.id,
            name=merchant.name,
            address=merchant.address,
            latitude=merchant.latitude,
            longitude=merchant.longitude,
            is_open=merchant.is_open if merchant.is_open is not None else True
        )
        db.add(db_merchant)
        db.commit()
        db.refresh(db_merchant)
        return db_merchant
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="创建商家时发生错误，请稍后重试"
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="创建商家时发生未知错误"
        )


@router.get("/{merchant_id}", response_model=MerchantResponse)
async def get_merchant(
    merchant_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取单个商家详情"""
    try:
        merchant = db.query(Merchant).filter(
            Merchant.id == merchant_id,
            Merchant.user_id == current_user.id
        ).first()
        if not merchant:
            raise HTTPException(status_code=404, detail="商家不存在")
        return merchant
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="获取商家详情时发生错误"
        )


@router.get("/{merchant_id}/prices", response_model=PaginatedResponse)
async def get_merchant_prices(
    merchant_id: int,
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(20, ge=1, le=100, description="每页记录数"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取商家的价格记录列表（分页）"""
    try:
        # 校验商家存在且属于当前用户
        merchant = db.query(Merchant).filter(
            Merchant.id == merchant_id,
            Merchant.user_id == current_user.id
        ).first()
        if not merchant:
            raise HTTPException(status_code=404, detail="商家不存在")

        query = db.query(ProductRecord).options(
            joinedload(ProductRecord.original_unit),
            joinedload(ProductRecord.standard_unit),
            joinedload(ProductRecord.merchant)
        ).filter(
            ProductRecord.user_id == current_user.id,
            ProductRecord.merchant_id == merchant_id
        )

        total = query.count()
        records = query.order_by(ProductRecord.recorded_at.desc()).offset(skip).limit(limit).all()

        items = [
            ProductRecordResponse(
                id=record.id,
                product_id=record.product_id,
                product_name=record.product_name,
                merchant_id=record.merchant_id,
                merchant_name=record.merchant.name if record.merchant else None,
                price=record.price,
                currency=record.currency,
                original_quantity=record.original_quantity,
                original_unit=record.original_unit.abbreviation if record.original_unit else "",
                standard_quantity=record.standard_quantity,
                standard_unit=record.standard_unit.abbreviation if record.standard_unit else "",
                record_type=record.record_type,
                exchange_rate=record.exchange_rate,
                recorded_at=record.recorded_at,
                notes=record.notes
            )
            for record in records
        ]

        page = (skip // limit) + 1
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=limit
        )
    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="获取商家价格记录时发生错误，请稍后重试"
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="获取商家价格记录时发生未知错误"
        )


@router.get("/{merchant_id}/product-prices")
async def get_merchant_product_prices(
    merchant_id: int,
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(20, ge=1, le=100, description="每页记录数"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取商家每个商品的最新价格，价格换算为该商品/原料默认单位的单价。"""
    from decimal import Decimal
    from app.services.unit_conversion_service import UnitConversionService

    try:
        # 校验商家存在且属于当前用户
        merchant = db.query(Merchant).filter(
            Merchant.id == merchant_id,
            Merchant.user_id == current_user.id
        ).first()
        if not merchant:
            raise HTTPException(status_code=404, detail="商家不存在")

        # 原生 SQL：CTE 取每商品最新价，外层 JOIN 出 standard_unit 缩写与
        # 商品关联原料的默认单位缩写，供 Python 层做单位换算。
        sql = text("""
            WITH latest AS (
                SELECT product_id, price, original_quantity, standard_quantity,
                       standard_unit_id, recorded_at,
                       ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY recorded_at DESC) AS rn
                FROM product_records
                WHERE user_id = :uid AND merchant_id = :mid
            )
            SELECT l.product_id, l.price, l.original_quantity, l.standard_quantity,
                   l.recorded_at,
                   su.abbreviation AS standard_unit_abbr,
                   su.unit_type     AS standard_unit_type,
                   du.abbreviation AS default_unit_abbr,
                   du.unit_type     AS default_unit_type,
                   p.name
            FROM latest l
            JOIN units su ON su.id = l.standard_unit_id
            JOIN products p ON p.id = l.product_id
            LEFT JOIN ingredients i ON i.id = p.ingredient_id
            LEFT JOIN units du ON du.id = i.default_unit_id
            WHERE l.rn = 1
            ORDER BY p.name ASC
            LIMIT :limit OFFSET :skip
        """)

        rows = db.execute(sql, {
            "uid": current_user.id,
            "mid": merchant_id,
            "limit": limit,
            "skip": skip,
        }).fetchall()

        # 去重后的商品总数（用于分页）
        count_sql = text("""
            SELECT COUNT(*) FROM (
                SELECT product_id,
                       ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY recorded_at DESC) AS rn
                FROM product_records
                WHERE user_id = :uid AND merchant_id = :mid
            ) WHERE rn = 1
        """)
        total = db.execute(count_sql, {"uid": current_user.id, "mid": merchant_id}).scalar() or 0

        unit_service = UnitConversionService(db)
        items = []
        for r in rows:
            price = float(r.price) if r.price else 0
            std_qty = float(r.standard_quantity) if r.standard_quantity else 0

            unit_price = None
            unit_label = None

            # 优先换算到商品/原料的默认单位
            if std_qty > 0 and r.default_unit_abbr and r.standard_unit_abbr:
                try:
                    result = unit_service.convert(
                        Decimal(str(std_qty)),
                        r.standard_unit_abbr,
                        r.default_unit_abbr,
                        "product",
                        r.product_id,
                    )
                    if result is not None:
                        target_qty = float(result[0])
                        if target_qty > 0:
                            unit_price = price / target_qty
                            unit_label = f"元/{r.default_unit_abbr}"
                except Exception:
                    unit_price = None
                    unit_label = None

            # 回退：按固定参考单位换算（质量->元/斤，体积->元/L）
            if unit_price is None and std_qty > 0:
                if r.standard_unit_type == "mass":
                    unit_price = price / std_qty * 500
                    unit_label = "元/斤"
                elif r.standard_unit_type == "volume":
                    unit_price = price / std_qty * 1000
                    unit_label = "元/L"

            items.append({
                "product_id": r.product_id,
                "product_name": r.name,
                "price": round(price, 2),
                "standard_unit_price": round(unit_price, 2) if unit_price is not None else None,
                "standard_unit_label": unit_label,
                "original_quantity": float(r.original_quantity) if r.original_quantity is not None else 0,
                "recorded_at": _to_iso(r.recorded_at),
            })

        page = (skip // limit) + 1 if limit else 1
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=limit
        )
    except HTTPException:
        raise
    except SQLAlchemyError:
        import traceback as _tb
        _tb.print_exc()
        raise HTTPException(
            status_code=500,
            detail="获取商家商品最新价格时发生错误，请稍后重试"
        )
    except Exception:
        import traceback as _tb
        _tb.print_exc()
        raise HTTPException(
            status_code=500,
            detail="获取商家商品最新价格时发生未知错误"
        )


@router.put("/{merchant_id}", response_model=MerchantResponse)
async def update_merchant(
    merchant_id: int,
    merchant: MerchantUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """更新商家信息"""
    try:
        db_merchant = db.query(Merchant).filter(
            Merchant.id == merchant_id,
            Merchant.user_id == current_user.id
        ).first()
        if not db_merchant:
            raise HTTPException(status_code=404, detail="商家不存在")

        # 更新字段
        update_data = merchant.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_merchant, key, value)

        db.commit()
        db.refresh(db_merchant)
        return db_merchant
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="更新商家时发生错误，请稍后重试"
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="更新商家时发生未知错误"
        )


@router.delete("/{merchant_id}")
async def delete_merchant(
    merchant_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """删除商家"""
    try:
        db_merchant = db.query(Merchant).filter(
            Merchant.id == merchant_id,
            Merchant.user_id == current_user.id
        ).first()
        if not db_merchant:
            raise HTTPException(status_code=404, detail="商家不存在")

        # 检查是否有关联的商品记录
        from app.models.product import ProductRecord
        record_count = db.query(ProductRecord).filter(
            ProductRecord.merchant_id == merchant_id
        ).count()
        if record_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"该商家还有 {record_count} 条价格记录，无法删除"
            )

        db.delete(db_merchant)
        db.commit()
        return {"message": "商家删除成功"}
    except HTTPException:
        raise
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="删除商家时发生错误，请稍后重试"
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="删除商家时发生未知错误"
        )


@router.get("", response_model=PaginatedResponse[MerchantResponse])
async def get_merchants(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(10, ge=1, le=100, description="每页记录数"),
    search: Optional[str] = Query(None, description="搜索关键词（商家名称或地址）"),
    include_closed: bool = Query(False, description="是否包含已关闭的商家"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取商家列表（支持分页和搜索）"""
    try:
        # 构建查询
        query = db.query(Merchant).filter(
            Merchant.user_id == current_user.id
        )

        # 默认只显示营业中的商家
        if not include_closed:
            query = query.filter(Merchant.is_open == True)

        # 添加搜索条件
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Merchant.name.like(search_pattern),
                    Merchant.address.like(search_pattern)
                )
            )

        # 获取总数
        total = query.count()

        # 分页查询
        merchants = query.order_by(Merchant.created_at.desc()).offset(skip).limit(limit).all()

        # 计算页码
        page = (skip // limit) + 1

        # 返回分页响应
        return PaginatedResponse.create(
            items=merchants,
            total=total,
            page=page,
            page_size=limit
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="获取商家列表时发生错误，请稍后重试"
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="获取商家列表时发生未知错误"
        )


@router.get("/favorites", response_model=List[FavoriteMerchantResponse])
async def get_favorite_merchants(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取常用商家"""
    try:
        favorites = db.query(FavoriteMerchant).filter(
            FavoriteMerchant.user_id == current_user.id
        ).order_by(FavoriteMerchant.created_at.desc()).all()
        return favorites
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="获取常用商家时发生错误，请稍后重试"
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="获取常用商家时发生未知错误"
        )


@router.post("/favorites", response_model=FavoriteMerchantResponse)
async def create_favorite_merchant(
    merchant: FavoriteMerchantCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建常用商家"""
    try:
        db_merchant = FavoriteMerchant(
            user_id=current_user.id,
            name=merchant.name,
            type=merchant.type,
            latitude=merchant.latitude,
            longitude=merchant.longitude
        )
        db.add(db_merchant)
        db.commit()
        db.refresh(db_merchant)
        return db_merchant
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="创建常用商家时发生错误，请稍后重试"
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="创建常用商家时发生未知错误"
        )


@router.post("/route", response_model=RouteCalculateResponse)
async def calculate_merchant_route(
    request: RouteCalculateRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """计算路线"""
    from_merchant = db.query(FavoriteMerchant).filter(
        FavoriteMerchant.id == request.from_location_id,
        FavoriteMerchant.user_id == current_user.id
    ).first()
    if not from_merchant:
        raise HTTPException(status_code=404, detail="起点商家不存在")

    to_merchant = db.query(Merchant).filter(
        Merchant.id == request.to_location_id,
        Merchant.user_id == current_user.id
    ).first()
    if not to_merchant:
        raise HTTPException(status_code=404, detail="终点商家不存在")

    try:
        # 计算路线
        result = calculate_route(
            (float(from_merchant.latitude), float(from_merchant.longitude)),
            (float(to_merchant.latitude), float(to_merchant.longitude)),
            request.travel_mode,
            request.map_provider
        )

        return RouteCalculateResponse(**result)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="无效的坐标数据"
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="计算路线时发生错误，请稍后重试"
        )
