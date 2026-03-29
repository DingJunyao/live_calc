# 价格记录 API - 支持通过食材别名搜索（最后修改: 2026-03-27 23:30）
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, text, or_, and_
from typing import List, Optional
from datetime import datetime, timedelta
import json
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.product import ProductRecord
from app.models.product_entity import Product
from app.models.nutrition import Ingredient
from app.schemas.product import (
    ProductRecordCreate,
    ProductRecordUpdate,
    ProductRecordResponse,
    ProductHistoryResponse
)
from app.schemas.common import PaginatedResponse
from app.utils.unit_converter import convert_to_standard
from app.services.unit_matcher import UnitMatcher

router = APIRouter()


def _make_alias_search_term(term: str) -> str:
    """生成用于搜索 JSON 别名数组的 Unicode 转义字符串

    SQLite 存储 JSON 时会将中文字符转为 Unicode 转义序列，
    如 "番茄" 会存储为 "\\u756a\\u8304"。
    此函数将搜索词转换为相同的格式以便匹配。
    """
    return json.dumps(term)[1:-1]  # 去掉 json.dumps 添加的引号


def _get_or_create_ingredient(db: Session, product_name: str, current_user) -> Ingredient:
    """获取或创建食材"""
    # 首先尝试查找已存在的食材
    ingredient = db.query(Ingredient).filter(
        Ingredient.name == product_name,
        Ingredient.is_active == True
    ).first()

    if ingredient:
        return ingredient

    # 如果不存在，创建新食材
    ingredient = Ingredient(
        name=product_name,
        is_imported=True,
        created_by=current_user.id,
        updated_by=current_user.id,
        is_active=True
    )
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)

    return ingredient


def _get_or_create_product(db: Session, product_name: str, current_user) -> Product:
    """获取或创建商品"""
    # 首先尝试查找已存在的同名商品
    product = db.query(Product).filter(
        Product.name == product_name,
        Product.is_active == True
    ).first()

    if product:
        return product

    # 如果不存在，创建新商品
    # 先获取或创建对应的食材
    ingredient = _get_or_create_ingredient(db, product_name, current_user)

    # 创建商品
    product = Product(
        name=product_name,
        ingredient_id=ingredient.id,
        created_by=current_user.id,
        updated_by=current_user.id,
        is_active=True
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    return product


@router.post("", response_model=ProductRecordResponse)
@router.post("/", response_model=ProductRecordResponse)
async def create_product_record(
    record: ProductRecordCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建商品记录"""
    try:
        # 获取当天汇率
        exchange_rate = 1.0  # TODO: 从汇率服务获取

        # 使用单位匹配器获取单位 ID
        matcher = UnitMatcher(db)
        original_unit_obj = matcher.match_or_create_unit(record.original_unit)

        # 单位转换
        standard_quantity, standard_unit_str = convert_to_standard(
            record.original_quantity,
            record.original_unit
        )

        # 获取标准单位对象
        standard_unit_obj = matcher.match_or_create_unit(standard_unit_str)

        # 处理商品ID
        if record.product_id:
            # 如果提供了 product_id，验证商品是否存在
            product = db.query(Product).filter(
                Product.id == record.product_id,
                Product.is_active == True
            ).first()
            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"商品ID {record.product_id} 不存在"
                )
            product_id = record.product_id
            product_name = product.name
        else:
            # 如果没有提供 product_id，自动创建或获取商品
            product = _get_or_create_product(db, record.product_name, current_user)
            product_id = product.id
            product_name = product.name

        # 创建记录
        db_record = ProductRecord(
            user_id=current_user.id,
            product_id=product_id,
            product_name=product_name,
            merchant_id=record.merchant_id,
            price=record.price,
            currency=record.currency,
            original_quantity=record.original_quantity,
            original_unit_id=original_unit_obj.id if original_unit_obj else None,
            standard_quantity=standard_quantity,
            standard_unit_id=standard_unit_obj.id if standard_unit_obj else None,
            record_type=record.record_type,
            exchange_rate=exchange_rate,
            notes=record.notes,
            recorded_at=record.recorded_at  # 使用自定义记录时间，如果为空则使用默认值
        )
        db.add(db_record)
        db.commit()

        # 重新查询以加载单位关系和商家关系
        db_record = db.query(ProductRecord).options(
            joinedload(ProductRecord.original_unit),
            joinedload(ProductRecord.standard_unit),
            joinedload(ProductRecord.merchant)
        ).filter(ProductRecord.id == db_record.id).first()

        # 手动构造响应对象，将 Unit 对象转换为字符串
        return ProductRecordResponse(
            id=db_record.id,
            product_id=db_record.product_id,
            product_name=db_record.product_name,
            merchant_id=db_record.merchant_id,
            merchant_name=db_record.merchant.name if db_record.merchant else None,
            price=db_record.price,
            currency=db_record.currency,
            original_quantity=db_record.original_quantity,
            original_unit=db_record.original_unit.abbreviation if db_record.original_unit else "",
            standard_quantity=db_record.standard_quantity,
            standard_unit=db_record.standard_unit.abbreviation if db_record.standard_unit else "",
            record_type=db_record.record_type,
            exchange_rate=db_record.exchange_rate,
            recorded_at=db_record.recorded_at,
            notes=db_record.notes
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"创建记录失败: {str(e)}"
        )


@router.get("", response_model=PaginatedResponse)
@router.get("/", response_model=PaginatedResponse)
async def get_product_records(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="每页记录数"),
    product_name: Optional[str] = Query(None, description="商品名称过滤"),
    search: Optional[str] = Query(None, description="搜索关键词（同product_name，向前兼容）"),
    product_id: Optional[int] = Query(None, description="商品ID过滤"),
    ingredient_id: Optional[int] = Query(None, description="原料ID过滤（查询关联商品的价格记录）"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    target_unit: Optional[str] = Query(None, description="目标单位（用于价格单位转换）"),
    sort_by: str = Query("created_at", enum=["created_at", "updated_at", "price_records"], description="排序方式"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取商品记录列表（分页）

    target_unit: 目标单位（如 'g', 'L', '斤'），价格记录将转换到该单位
    如果不指定，使用原始记录的单位

    sort_by: 排序方式
        - created_at: 按创建时间排序（默认，即按记录时间倒序）
        - updated_at: 按更新时间排序
        - price_records: 按商品的价格记录数量排序
    """
    from sqlalchemy import func
    from app.services.unit_conversion_service import UnitConversionService
    
    # 初始化单位转换服务（如果需要转换）
    unit_service = UnitConversionService(db) if target_unit else None
    
    # 获取原料名称（用于单位转换）
    ingredient_name = None
    if ingredient_id and unit_service:
        ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if ingredient:
            ingredient_name = ingredient.name

    # 根据排序方式构建查询
    if sort_by == "price_records":
        # 按价格记录数量排序：将记录按其所属商品的总记录数量进行排序
        # 为此，我们将查询每个记录及其所属商品的记录数量

        # 子查询：计算每个商品的价格记录数量
        record_counts = db.query(
            ProductRecord.product_id,
            func.count(ProductRecord.id).label('record_count')
        ).filter(
            ProductRecord.user_id == current_user.id
        )

        # 应用过滤条件
        if ingredient_id:
            product_ids = db.query(Product.id).filter(
                Product.ingredient_id == ingredient_id,
                Product.is_active == True
            ).all()
            product_ids = [pid[0] for pid in product_ids]
            record_counts = record_counts.filter(ProductRecord.product_id.in_(product_ids))
        elif product_id:
            record_counts = record_counts.filter(ProductRecord.product_id == product_id)
        else:
            search_term = search or product_name
            if search_term:
                # 搜索商品名称或关联食材的别名
                alias_search = _make_alias_search_term(search_term)
                record_counts = record_counts.join(ProductRecord.product).join(
                    Product.ingredient
                ).filter(
                    or_(
                        ProductRecord.product_name.contains(search_term),
                        Ingredient.name.contains(search_term),
                        Ingredient.aliases.contains(alias_search)
                    )
                )
                print(f"[DEBUG] products.py - 搜索价格记录: {search_term}, 别名搜索: {alias_search}")

        # 添加日期范围过滤
        if start_date:
            if start_date.tzinfo:
                start_date = datetime.fromtimestamp(start_date.timestamp())
            record_counts = record_counts.filter(ProductRecord.recorded_at >= start_date)
        if end_date:
            if end_date.tzinfo:
                end_date = datetime.fromtimestamp(end_date.timestamp())
            record_counts = record_counts.filter(ProductRecord.recorded_at <= end_date)

        record_counts = record_counts.group_by(ProductRecord.product_id).subquery()

        # 主查询：获取记录，并关联商品的记录数量
        query = db.query(ProductRecord).outerjoin(
            record_counts, ProductRecord.product_id == record_counts.c.product_id
        ).options(
            joinedload(ProductRecord.original_unit),
            joinedload(ProductRecord.standard_unit),
            joinedload(ProductRecord.merchant)
        ).filter(
            ProductRecord.user_id == current_user.id
        )

        # 应用过滤条件到主查询
        if ingredient_id:
            product_ids = db.query(Product.id).filter(
                Product.ingredient_id == ingredient_id,
                Product.is_active == True
            ).all()
            product_ids = [pid[0] for pid in product_ids]
            query = query.filter(ProductRecord.product_id.in_(product_ids))
        elif product_id:
            query = query.filter(ProductRecord.product_id == product_id)
        else:
            search_term = search or product_name
            if search_term:
                # 搜索商品名称或关联食材的别名
                alias_search = _make_alias_search_term(search_term)
                query = query.join(ProductRecord.product).join(
                    Product.ingredient
                ).filter(
                    or_(
                        ProductRecord.product_name.contains(search_term),
                        Ingredient.name.contains(search_term),
                        Ingredient.aliases.contains(alias_search)
                    )
                )

        # 添加日期范围过滤
        if start_date:
            if start_date.tzinfo:
                start_date = datetime.fromtimestamp(start_date.timestamp())
            query = query.filter(ProductRecord.recorded_at >= start_date)
        if end_date:
            if end_date.tzinfo:
                end_date = datetime.fromtimestamp(end_date.timestamp())
            query = query.filter(ProductRecord.recorded_at <= end_date)

        total = query.count()

        # 按商品的价格记录数量排序，然后按记录时间排序（为了稳定性）
        records = query.order_by(record_counts.c.record_count.desc(), ProductRecord.recorded_at.desc()).offset(skip).limit(limit).all()
    else:
        # 使用原有逻辑
        query = db.query(ProductRecord).options(
            joinedload(ProductRecord.original_unit),
            joinedload(ProductRecord.standard_unit),
            joinedload(ProductRecord.merchant)
        ).filter(ProductRecord.user_id == current_user.id)

        # 优先使用 ingredient_id 过滤（通过关联商品）
        if ingredient_id:
            # 通过 ingredient_id 查找所有关联的商品
            product_ids = db.query(Product.id).filter(
                Product.ingredient_id == ingredient_id,
                Product.is_active == True
            ).all()
            product_ids = [pid[0] for pid in product_ids]
            query = query.filter(ProductRecord.product_id.in_(product_ids))
        # 然后使用 product_id 过滤
        elif product_id:
            query = query.filter(ProductRecord.product_id == product_id)
        # 最后使用search参数（优先）或product_name参数进行过滤
        else:
            search_term = search or product_name
            if search_term:
                # 搜索商品名称或关联食材的别名
                alias_search = _make_alias_search_term(search_term)
                query = query.join(ProductRecord.product).join(
                    Product.ingredient
                ).filter(
                    or_(
                        ProductRecord.product_name.contains(search_term),
                        Ingredient.name.contains(search_term),
                        Ingredient.aliases.contains(alias_search)
                    )
                )

        # 添加日期范围过滤
        if start_date:
            # 如果输入时间带有时区信息，转换为本地时间（naive datetime）
            if start_date.tzinfo:
                # 先转换为时间戳，再转换为本地时间
                start_date = datetime.fromtimestamp(start_date.timestamp())
            query = query.filter(ProductRecord.recorded_at >= start_date)
        if end_date:
            # 如果输入时间带有时区信息，转换为本地时间（naive datetime）
            if end_date.tzinfo:
                # 先转换为时间戳，再转换为本地时间
                end_date = datetime.fromtimestamp(end_date.timestamp())
            query = query.filter(ProductRecord.recorded_at <= end_date)

        total = query.count()

        # 按时间排序
        if sort_by == "updated_at":
            records = query.order_by(ProductRecord.updated_at.desc()).offset(skip).limit(limit).all()
        else:  # 默认按创建时间排序
            records = query.order_by(ProductRecord.recorded_at.desc()).offset(skip).limit(limit).all()
    page = skip // limit + 1

    # 手动构造响应列表，处理单位转换
    items = []
    for record in records:
        # 确定要显示的数量和单位
        if target_unit and unit_service and record.original_unit:
            # 需要单位转换
            original_unit_abbr = record.original_unit.abbreviation
            original_quantity = float(record.original_quantity)
            
            # 尝试转换数量到目标单位
            converted_quantity = unit_service.convert(
                original_quantity,
                original_unit_abbr,
                target_unit,
                ingredient_name
            )
            
            if converted_quantity is not None:
                # 转换成功，使用转换后的数量和目标单位
                display_quantity = converted_quantity
                display_unit = target_unit
            else:
                # 转换失败，使用原始值
                display_quantity = original_quantity
                display_unit = original_unit_abbr
        else:
            # 不需要转换，使用原始值
            display_quantity = float(record.original_quantity)
            display_unit = record.original_unit.abbreviation if record.original_unit else ""
        
        items.append(
            ProductRecordResponse(
                id=record.id,
                product_id=record.product_id,
                product_name=record.product_name,
                merchant_id=record.merchant_id,
                merchant_name=record.merchant.name if record.merchant else None,
                price=float(record.price),  # 总价保持不变
                currency=record.currency,
                original_quantity=display_quantity,  # 使用转换后的数量
                original_unit=display_unit,  # 使用转换后的单位
                standard_quantity=record.standard_quantity,
                standard_unit=record.standard_unit.abbreviation if record.standard_unit else "",
                record_type=record.record_type,
                exchange_rate=record.exchange_rate,
                recorded_at=record.recorded_at,
                notes=record.notes
            )
        )

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        page_size=limit
    )


@router.get("/{record_id}", response_model=ProductRecordResponse)
async def get_product_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取商品记录详情"""
    record = db.query(ProductRecord).options(
        joinedload(ProductRecord.original_unit),
        joinedload(ProductRecord.standard_unit),
        joinedload(ProductRecord.merchant)
    ).filter(
        ProductRecord.id == record_id,
        ProductRecord.user_id == current_user.id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 手动构造响应对象，将 Unit 对象转换为字符串
    return ProductRecordResponse(
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


@router.put("/{record_id}", response_model=ProductRecordResponse)
async def update_product_record(
    record_id: int,
    record: ProductRecordUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """更新价格记录"""
    try:
        # 查找记录
        db_record = db.query(ProductRecord).options(
            joinedload(ProductRecord.original_unit),
            joinedload(ProductRecord.standard_unit),
            joinedload(ProductRecord.merchant)
        ).filter(
            ProductRecord.id == record_id,
            ProductRecord.user_id == current_user.id
        ).first()

        if not db_record:
            raise HTTPException(status_code=404, detail="价格记录不存在")

        # 更新单位（如果需要）
        if record.original_unit:
            matcher = UnitMatcher(db)
            original_unit_obj = matcher.match_or_create_unit(record.original_unit)
        else:
            original_unit_obj = db_record.original_unit

        # 单位转换
        if record.original_quantity and record.original_unit:
            standard_quantity, standard_unit_str = convert_to_standard(
                record.original_quantity,
                record.original_unit
            )
            standard_unit_obj = matcher.match_or_create_unit(standard_unit_str)
        else:
            standard_quantity = db_record.standard_quantity
            standard_unit_obj = db_record.standard_unit

        # 更新字段
        update_data = record.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key not in ['original_unit', 'original_quantity']:  # 单位需要特殊处理
                setattr(db_record, key, value)

        # 更新单位相关字段
        if record.original_unit:
            db_record.original_unit_id = original_unit_obj.id if original_unit_obj else None
        if standard_unit_obj:
            db_record.standard_quantity = standard_quantity
            db_record.standard_unit_id = standard_unit_obj.id if standard_unit_obj else None

        db.commit()
        db.refresh(db_record)

        # 手动构造响应对象，将 Unit 对象转换为字符串
        return ProductRecordResponse(
            id=db_record.id,
            product_id=db_record.product_id,
            product_name=db_record.product_name,
            merchant_id=db_record.merchant_id,
            merchant_name=db_record.merchant.name if db_record.merchant else None,
            price=db_record.price,
            currency=db_record.currency,
            original_quantity=db_record.original_quantity,
            original_unit=db_record.original_unit.abbreviation if db_record.original_unit else "",
            standard_quantity=db_record.standard_quantity,
            standard_unit=db_record.standard_unit.abbreviation if db_record.standard_unit else "",
            record_type=db_record.record_type,
            exchange_rate=db_record.exchange_rate,
            recorded_at=db_record.recorded_at,
            notes=db_record.notes
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"更新记录失败: {str(e)}"
        )


@router.delete("/{record_id}")
async def delete_product_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """删除价格记录"""
    try:
        db_record = db.query(ProductRecord).filter(
            ProductRecord.id == record_id,
            ProductRecord.user_id == current_user.id
        ).first()

        if not db_record:
            raise HTTPException(status_code=404, detail="价格记录不存在")

        db.delete(db_record)
        db.commit()
        return {"message": "价格记录删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"删除记录失败: {str(e)}"
        )


@router.get("/history/{product_name}", response_model=ProductHistoryResponse)
async def get_product_history(
    product_name: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取商品历史价格"""
    records = db.query(ProductRecord).options(
        joinedload(ProductRecord.original_unit),
        joinedload(ProductRecord.standard_unit),
        joinedload(ProductRecord.merchant)
    ).filter(
        ProductRecord.user_id == current_user.id,
        ProductRecord.product_name == product_name
    ).order_by(ProductRecord.recorded_at.desc()).all()

    # 处理所有记录，将 Unit 对象转换为字符串
    processed_records = [
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

    return ProductHistoryResponse(
        product_name=product_name,
        records=processed_records
    )

