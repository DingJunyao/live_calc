"""商品实体 API 路由"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, and_, or_, func
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user
from app.api.deps import get_timezone
from app.utils.date_range_utils import utc_datetime_to_local_date, local_date_range_to_utc_range
from app.models.user import User
from app.models.product_entity import Product
from app.models.product_barcode import ProductBarcode
from app.models.product import ProductRecord
from app.models.nutrition import Ingredient
from app.schemas.product_entity import (
    ProductCreate, ProductUpdate, ProductResponse, ProductWithDetails,
    ProductBarcodeCreate, ProductBarcodeUpdate, ProductBarcodeResponse,
    ImportAliasRequest
)
from app.schemas.common import PaginatedResponse
from app.utils.database_helpers import serialize_tags, deserialize_tags, json_text_contains
from app.utils.datetime_utils import serialize_datetime
from app.services.proposals import service as proposal_service

router = APIRouter(tags=["products_entity"])


def _apply_product_special_conditions(query, no_price, single_price, single_merchant):
    """Apply special condition filters to a Product query."""
    from app.models.product import ProductRecord
    from sqlalchemy import exists, select

    if no_price:
        query = query.filter(
            ~exists().where(ProductRecord.product_id == Product.id)
        )

    if single_price:
        subq = (
            select(func.count())
            .select_from(ProductRecord)
            .where(ProductRecord.product_id == Product.id)
            .correlate(Product)
            .scalar_subquery()
        )
        query = query.filter(subq == 1)

    if single_merchant:
        subq = (
            select(func.count(func.distinct(ProductRecord.merchant_id)))
            .select_from(ProductRecord)
            .where(ProductRecord.product_id == Product.id)
            .correlate(Product)
            .scalar_subquery()
        )
        query = query.filter(subq == 1)

    return query


@router.post("/products/entity", response_model=ProductResponse)
@router.post("/products/entity/", response_model=ProductResponse)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建商品"""
    # 检查条码唯一性
    if product.barcode:
        existing = db.query(Product).filter(Product.barcode == product.barcode).first()
        if existing:
            raise HTTPException(status_code=400, detail="Barcode already exists")

    # 将 Pydantic 对象转换为字典并序列化 tags
    product_data = product.model_dump()
    if 'tags' in product_data:
        product_data['tags'] = serialize_tags(product_data['tags'])

    db_product = Product(**product_data)
    db_product.created_by = current_user.id
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    # 反序列化 tags 用于响应
    if db_product.tags:
        db_product.tags = deserialize_tags(db_product.tags)
    else:
        db_product.tags = []

    # 填充原料名称
    db_product.ingredient_name = db_product.ingredient.name if db_product.ingredient else None

    return db_product


@router.get("/products/entity", response_model=PaginatedResponse)
@router.get("/products/entity/", response_model=PaginatedResponse)
def list_products(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="每页记录数"),
    ingredient_id: Optional[int] = Query(None, description="原料ID过滤"),
    search: Optional[str] = Query(None, description="搜索关键词（商品名称或食材别名）"),
    sort_by: str = Query("created_at", enum=["created_at", "updated_at", "price_records"], description="排序方式"),
    ingredient_ids: Optional[str] = Query(None, description="原料ID列表，逗号分隔"),
    ingredient_category_ids: Optional[str] = Query(None, description="原料分类ID列表，逗号分隔"),
    brands: Optional[str] = Query(None, description="品牌列表，逗号分隔"),
    no_price: bool = Query(False, description="筛选没有维护过价格的商品"),
    single_price: bool = Query(False, description="筛选仅有一条价格记录的商品"),
    single_merchant: bool = Query(False, description="筛选仅有一家商家有其价格记录的商品"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取商品列表（分页）

    支持通过商品名称或关联食材的别名搜索。
    例如：搜索"西"可以找到商品"番茄"（如果其关联食材有别名"西红柿"）
    """
    from sqlalchemy import func

    # 根据排序方式构建查询
    if sort_by == "price_records":
        # 按价格记录数量排序：计算每个商品的价格记录数量，然后按数量排序
        subquery = db.query(
            Product.id.label('product_id'),
            func.count(ProductRecord.id).label('record_count')
        ).outerjoin(
            ProductRecord, Product.id == ProductRecord.product_id
        ).filter(Product.is_active == True).group_by(Product.id).subquery()

        # 然后将此子查询与主查询连接
        query = db.query(Product).options(
            joinedload(Product.ingredient)
        ).join(
            subquery, Product.id == subquery.c.product_id
        ).filter(Product.is_active == True)

        if ingredient_id:
            query = query.filter(Product.ingredient_id == ingredient_id)

        if search:
            # 搜索商品名称、商品别名或食材别名
            search_filter = or_(
                Product.name.contains(search),
                json_text_contains(Product.aliases, search),
                Product.ingredient.has(
                    or_(
                        Ingredient.name.contains(search),
                        json_text_contains(Ingredient.aliases, search)
                    )
                )
            )
            query = query.filter(search_filter)

        if ingredient_ids:
            ids = [int(x.strip()) for x in ingredient_ids.split(',') if x.strip()]
            if ids:
                query = query.filter(Product.ingredient_id.in_(ids))

        if ingredient_category_ids:
            cat_ids = [int(x.strip()) for x in ingredient_category_ids.split(',') if x.strip()]
            if cat_ids:
                query = query.filter(Product.ingredient.has(Ingredient.category_id.in_(cat_ids)))

        if brands:
            brand_list = [b.strip() for b in brands.split(',') if b.strip()]
            if brand_list:
                query = query.filter(Product.brand.in_(brand_list))

        # 应用特殊条件过滤
        query = _apply_product_special_conditions(query, no_price, single_price, single_merchant)

        total = query.count()

        # 按价格记录数量排序，然后按商品创建时间排序以确保一致性
        products = query.order_by(desc(subquery.c.record_count), desc(Product.created_at)).offset(skip).limit(limit).all()
    else:
        # 使用原有逻辑
        query = db.query(Product).options(
            joinedload(Product.ingredient)
        ).filter(Product.is_active == True)

        if ingredient_id:
            query = query.filter(Product.ingredient_id == ingredient_id)

        if search:
            # 搜索商品名称、商品别名或食材别名
            search_filter = or_(
                Product.name.contains(search),
                json_text_contains(Product.aliases, search),
                Product.ingredient.has(
                    or_(
                        Ingredient.name.contains(search),
                        json_text_contains(Ingredient.aliases, search)
                    )
                )
            )
            query = query.filter(search_filter)

        if ingredient_ids:
            ids = [int(x.strip()) for x in ingredient_ids.split(',') if x.strip()]
            if ids:
                query = query.filter(Product.ingredient_id.in_(ids))

        if ingredient_category_ids:
            cat_ids = [int(x.strip()) for x in ingredient_category_ids.split(',') if x.strip()]
            if cat_ids:
                query = query.filter(Product.ingredient.has(Ingredient.category_id.in_(cat_ids)))

        if brands:
            brand_list = [b.strip() for b in brands.split(',') if b.strip()]
            if brand_list:
                query = query.filter(Product.brand.in_(brand_list))

        # 应用特殊条件过滤
        query = _apply_product_special_conditions(query, no_price, single_price, single_merchant)

        total = query.count()

        # 按时间排序
        if sort_by == "updated_at":
            products = query.order_by(desc(Product.updated_at)).offset(skip).limit(limit).all()
        else:  # 默认按创建时间排序
            products = query.order_by(desc(Product.created_at)).offset(skip).limit(limit).all()
    page = skip // limit + 1

    # 反序列化 tags 并填充 ingredient_name，然后构造响应对象
    items = []
    for product in products:
        if product.tags:
            product.tags = deserialize_tags(product.tags)
        else:
            product.tags = []
        # 填充原料名称
        product.ingredient_name = product.ingredient.name if product.ingredient else None

        # 将 Product 对象转换为 dict 以便正确序列化
        items.append({
            "id": product.id,
            "name": product.name,
            "brand": product.brand,
            "barcode": product.barcode,
            "image_url": product.image_url,
            "ingredient_id": product.ingredient_id,
            "ingredient_name": product.ingredient_name,
            "tags": product.tags,
            "aliases": product.aliases or [],
            "created_at": serialize_datetime(product.created_at) if product.created_at else None,
            "updated_at": serialize_datetime(product.updated_at) if product.updated_at else None,
            "is_active": product.is_active
        })

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        page_size=limit
    )


@router.get("/products/entity/{product_id}", response_model=ProductWithDetails)
@router.get("/products/entity/{product_id}/", response_model=ProductWithDetails)
def get_product(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), tz: str = Depends(get_timezone)):
    """获取商品详情"""
    product = db.query(Product).options(
        joinedload(Product.ingredient)
    ).filter(Product.id == product_id, Product.is_active == True).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 反序列化 tags
    if product.tags:
        product.tags = deserialize_tags(product.tags)
    else:
        product.tags = []

    from sqlalchemy import func

    # 获取最近有记录的日期
    all_dates = db.query(ProductRecord.recorded_at).filter(
        ProductRecord.product_id == product_id,
        ProductRecord.is_active == True,
    ).all()
    latest_date = max((utc_datetime_to_local_date(d[0], tz) for d in all_dates), default=None)

    latest_price = None
    latest_price_unit = None
    latest_price_date = None

    if latest_date:
        # 取最近一天（用户本地日）的所有记录
        day_start, day_end = local_date_range_to_utc_range(latest_date, latest_date, tz)
        day_records = db.query(ProductRecord).options(
            joinedload(ProductRecord.original_unit)
        ).filter(
            ProductRecord.product_id == product_id,
            ProductRecord.recorded_at >= day_start,
            ProductRecord.recorded_at <= day_end,
            ProductRecord.is_active == True
        ).all()

        if day_records:
            from decimal import Decimal
            from app.services.unit_conversion_service import UnitConversionService
            unit_service = UnitConversionService(db)

            # 按当前用户的质量偏好单位折算（fallback 斤）
            target_unit_abbr = "斤"
            _mui = getattr(current_user, "default_mass_unit_id", None)
            if _mui:
                from app.models.unit import Unit as _U
                _mu = db.query(_U).filter(_U.id == _mui).first()
                if _mu and _mu.abbreviation:
                    target_unit_abbr = _mu.abbreviation

            unit_prices = []
            for record in day_records:
                if record.price and record.original_quantity and record.original_quantity > 0:
                    total_price = float(record.price)
                    original_quantity = float(record.original_quantity)
                    original_unit_abbr = record.original_unit.abbreviation if record.original_unit else None

                    if original_unit_abbr:
                        if target_unit_abbr and original_unit_abbr != target_unit_abbr:
                            convert_result = unit_service.convert(
                                Decimal(str(original_quantity)),
                                original_unit_abbr,
                                target_unit_abbr,
                                entity_type="product",
                                entity_id=product_id,
                            )
                            if convert_result is not None:
                                converted_quantity, _ = convert_result
                                if converted_quantity and float(converted_quantity) > 0:
                                    unit_prices.append(total_price / float(converted_quantity))
                                    continue
                        # 单位相同或转换失败，直接算单价
                        unit_prices.append(total_price / original_quantity)
                    else:
                        unit_prices.append(total_price / original_quantity)

            if unit_prices:
                latest_price = sum(unit_prices) / len(unit_prices)
                latest_price_unit = target_unit_abbr
                latest_price_date = datetime.strptime(latest_date, '%Y-%m-%d') if isinstance(latest_date, str) else latest_date

    # 构建详细响应
    ingredient_name = product.ingredient.name if product.ingredient else None
    response = ProductWithDetails(
        **product.__dict__,
        ingredient_name=ingredient_name,
        latest_price=latest_price,
        latest_price_unit=latest_price_unit,
        latest_price_date=latest_price_date
    )

    # 非管理员追加 pending_proposal
    if not getattr(current_user, "is_admin", False):
        from app.services.proposals.pending import get_pending_proposal
        pp = get_pending_proposal(db, "product", product_id, current_user.id)
        if pp:
            response.pending_proposal = {"id": pp.id, "action": pp.action, "payload": pp.payload}

    return response


@router.put("/products/entity/{product_id}", response_model=ProductResponse)
@router.put("/products/entity/{product_id}/", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新商品

    管理员可修改任意商品，普通用户只能修改自己创建的商品。
    """
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="商品不存在")

    update_data = product_update.model_dump(exclude_unset=True)

    # 检查条码唯一性（端点提交时）
    if 'barcode' in update_data and update_data['barcode']:
        existing = db.query(Product).filter(
            Product.barcode == update_data['barcode'],
            Product.id != product_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Barcode already exists")

    # 序列化 tags
    if 'tags' in update_data:
        update_data['tags'] = serialize_tags(update_data['tags'])

    update_data["updated_by"] = current_user.id

    # 全局 price_weight 仅管理员可改；普通用户提交时剔除（连同审核提议都不开）
    if not current_user.is_admin and "price_weight" in update_data:
        update_data.pop("price_weight", None)

    # 分流：管理员直写 / 普通用户提议（全 manual）
    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="product", entity_id=product_id,
            action="update", payload=update_data, admin=current_user,
        )
    else:
        proposal_service.submit(
            db, entity_type="product", entity_id=product_id,
            action="update", payload=update_data, proposer=current_user,
        )
    db.commit()
    db.refresh(db_product)

    # 反序列化 tags 用于响应
    if db_product.tags:
        db_product.tags = deserialize_tags(db_product.tags)
    else:
        db_product.tags = []
    db_product.ingredient_name = db_product.ingredient.name if db_product.ingredient else None
    return db_product


@router.delete("/products/entity/{product_id}")
@router.delete("/products/entity/{product_id}/")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """软删除商品及其所有价格记录

    管理员可删除任意商品，普通用户只能删除自己创建的商品（created_by）。
    如果商品是其所属原料的唯一活跃商品，则不允许删除。
    """
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 唯一商品检查（端点提交时；执行器 apply 时再查一次防审核期间变化）
    sibling_count = db.query(Product).filter(
        Product.ingredient_id == db_product.ingredient_id,
        Product.is_active == True,
        Product.id != product_id
    ).count()
    if sibling_count == 0:
        raise HTTPException(
            status_code=400,
            detail=f"「{db_product.name}」是其所属原料的唯一商品，无法删除。请先为该原料添加其他商品后再删除。"
        )

    # 分流：管理员直写（级联软删在执行器）/ 普通用户提议待审
    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="product", entity_id=product_id,
            action="delete", payload={}, admin=current_user,
        )
        db.commit()
        return {"message": "商品已删除（管理员直写，级联软删价格记录）"}

    p = proposal_service.submit(
        db, entity_type="product", entity_id=product_id,
        action="delete", payload={}, proposer=current_user,
    )
    db.commit()
    return {"message": f"删除提议已提交（proposal_id={p.id}, status={p.status}）"}


# ==================== 条码管理端点 ====================

@router.post("/products/entity/{product_id}/barcodes", response_model=ProductBarcodeResponse)
def add_product_barcode(
    product_id: int,
    barcode: ProductBarcodeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """为商品添加条码"""
    # 验证商品是否存在
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 检查条码是否已存在（全局唯一）
    existing_barcode = db.query(ProductBarcode).filter(
        ProductBarcode.barcode == barcode.barcode
    ).first()
    if existing_barcode:
        raise HTTPException(status_code=400, detail="Barcode already exists")

    # 如果设置为主条码，需要先将该商品的其他主条码取消
    if barcode.is_primary:
        db.query(ProductBarcode).filter(
            ProductBarcode.product_id == product_id,
            ProductBarcode.is_primary == True
        ).update({"is_primary": False})

    # 创建新条码
    new_barcode = ProductBarcode(
        product_id=product_id,
        barcode=barcode.barcode,
        barcode_type=barcode.barcode_type,
        is_primary=barcode.is_primary,
        created_by=current_user.id,
        updated_by=current_user.id
    )

    db.add(new_barcode)
    db.commit()
    db.refresh(new_barcode)

    return new_barcode


@router.get("/products/entity/{product_id}/barcodes", response_model=List[ProductBarcodeResponse])
def get_product_barcodes(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取商品的所有条码"""
    # 验证商品是否存在
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    barcodes = db.query(ProductBarcode).filter(
        ProductBarcode.product_id == product_id,
        ProductBarcode.is_active == True
    ).order_by(ProductBarcode.is_primary.desc(), ProductBarcode.created_at).all()

    return barcodes


@router.put("/products/entity/barcodes/{barcode_id}", response_model=ProductBarcodeResponse)
def update_product_barcode(
    barcode_id: int,
    barcode_update: ProductBarcodeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """更新条码信息"""
    barcode = db.query(ProductBarcode).filter(ProductBarcode.id == barcode_id).first()
    if not barcode:
        raise HTTPException(status_code=404, detail="Barcode not found")

    # 如果设置为主条码，需要先将该商品的其他主条码取消
    if barcode_update.is_primary is True:
        db.query(ProductBarcode).filter(
            ProductBarcode.product_id == barcode.product_id,
            ProductBarcode.id != barcode_id,
            ProductBarcode.is_primary == True
        ).update({"is_primary": False})

    # 更新字段
    update_data = barcode_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(barcode, field, value)

    barcode.updated_by = current_user.id
    db.commit()
    db.refresh(barcode)

    return barcode


@router.delete("/products/entity/barcodes/{barcode_id}")
def delete_product_barcode(
    barcode_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """删除条码（软删除）"""
    barcode = db.query(ProductBarcode).filter(ProductBarcode.id == barcode_id).first()
    if not barcode:
        raise HTTPException(status_code=404, detail="Barcode not found")

    barcode.is_active = False
    barcode.updated_by = current_user.id
    db.commit()


@router.get("/products/entity/{product_id}/latest-price")
def get_product_latest_price(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取商品的最近价格 - 计算平均单价

    - **product_id**: 商品ID

    返回该商品关联的最近一天所有价格记录的平均单价（单位归一化到 ¥/斤）。
    P2：价格跨用户公开，响应去标识（不含 user_id/record_type）。
    """
    try:
        from datetime import datetime, timedelta
        from collections import Counter

        # PostgreSQL 返回 aware datetime，统一转 naive 比较
        def _naive(dt):
            if dt is None:
                return None
            return dt.replace(tzinfo=None) if dt.tzinfo else dt

        # 查询该商品的所有价格记录（P2：跨用户公开，不按 user_id 过滤）
        all_records = db.query(ProductRecord).filter(
            ProductRecord.product_id == product_id
        ).order_by(ProductRecord.recorded_at.desc()).all()

        if not all_records:
            return {
                "average_price": None,
                "unit": None
            }

        # 首先尝试获取最近24小时内的记录
        now = datetime.utcnow()
        one_day_ago = now - timedelta(days=1)

        recent_records = [r for r in all_records if _naive(r.recorded_at) is not None and _naive(r.recorded_at) >= one_day_ago]

        # 如果最近24小时内没有记录，则查找最近一次记录的那一天的所有记录
        if not recent_records:
            # 最近一次记录的日期
            latest_date = _naive(all_records[0].recorded_at).date()
            recent_records = [r for r in all_records if _naive(r.recorded_at).date() == latest_date]

        if not recent_records:
            return {
                "average_price": None,
                "unit": None
            }

        # 计算平均价格 - 使用单价而非总价
        # 使用 standard_quantity（克）归一化到 ¥/斤，确保跨单位可比较
        unit_prices = []
        for record in recent_records:
            std_qty = record.standard_quantity
            if record.price is not None and std_qty is not None and float(std_qty) > 0:
                unit_price = float(record.price) * 500.0 / float(std_qty)
                unit_prices.append(unit_price)

        if not unit_prices:
            return {
                "average_price": None,
                "unit": None
            }

        average_price = sum(unit_prices) / len(unit_prices)  # 元/斤

        # 按当前用户的质量偏好单位折算（fallback 斤；跨类不可转则保持斤）
        target_unit_abbr = "斤"
        display_price = average_price
        _mui = getattr(current_user, "default_mass_unit_id", None)
        if _mui:
            from app.models.unit import Unit as _U
            _mu = db.query(_U).filter(_U.id == _mui).first()
            if _mu and _mu.abbreviation and _mu.abbreviation != "斤":
                try:
                    from app.services.unit_conversion_service import UnitConversionService
                    _conv = UnitConversionService(db).convert(1, "斤", _mu.abbreviation)
                    if _conv and float(_conv[0]) > 0:
                        display_price = average_price / float(_conv[0])
                        target_unit_abbr = _mu.abbreviation
                except Exception:
                    pass

        return {
            "average_price": round(display_price, 2),
            "unit": target_unit_abbr
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取最近价格失败: {str(e)}")


@router.get("/products/entity/{product_id}/latest-price-by-merchant")
def get_product_latest_price_by_merchant(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取商品按商家分组的最新价格

    返回每个商家的最新一条价格记录（已转换为关联原料默认单位，缺失时回退原价）。
    按价格从低到高排序，并标注最低价。
    P2：价格跨用户公开，响应去标识（不含 user_id/record_type）。
    """
    try:
        from app.models.merchant import Merchant

        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return {"prices": [], "unit": None}

        # 原料默认单位字段已迁移至用户级偏好；目标单位留空，下游按记录原单位处理
        target_unit_abbr = None

        # P2：跨用户公开查询价格记录（不按 user_id 过滤）
        records = db.query(ProductRecord).options(
            joinedload(ProductRecord.original_unit),
            joinedload(ProductRecord.merchant)
        ).join(
            Merchant, ProductRecord.merchant_id == Merchant.id
        ).filter(
            ProductRecord.product_id == product_id,
            ProductRecord.merchant_id.isnot(None),
            Merchant.is_open == True
        ).order_by(ProductRecord.recorded_at.desc()).all()

        # 按商家分组，每组只保留最新一条
        merchant_latest: dict = {}
        for record in records:
            mid = record.merchant_id
            if mid not in merchant_latest:
                merchant_latest[mid] = record

        unit_service = None
        results = []
        for mid, record in merchant_latest.items():
            if record.price is None or record.original_quantity is None or record.original_quantity <= 0 or not record.original_unit:
                continue

            total_price = float(record.price)
            original_quantity = float(record.original_quantity)
            original_unit_abbr = record.original_unit.abbreviation

            unit_price = None
            # 如果有关联原料且有默认单位，尝试转换
            if target_unit_abbr and original_unit_abbr != target_unit_abbr and product.ingredient_id:
                if unit_service is None:
                    from app.services.unit_conversion_service import UnitConversionService
                    unit_service = UnitConversionService(db)
                convert_result = unit_service.convert(
                    original_quantity,
                    original_unit_abbr,
                    target_unit_abbr,
                    entity_type="ingredient",
                    entity_id=product.ingredient_id,
                )
                if convert_result is not None:
                    converted_quantity, _ = convert_result
                    if converted_quantity and float(converted_quantity) > 0:
                        unit_price = total_price / float(converted_quantity)

            if unit_price is None:
                unit_price = total_price / original_quantity

            # 响应去标识：只保留价格维度信息，不含 user_id/record_type
            results.append({
                "merchant_id": mid,
                "merchant_name": record.merchant.name if record.merchant else f"商家#{mid}",
                "price": round(unit_price, 2),
                "unit": target_unit_abbr or original_unit_abbr,
                "recorded_at": serialize_datetime(record.recorded_at) if record.recorded_at else None,
                "product_name": record.product_name,
            })

        results.sort(key=lambda x: x["price"])

        if results:
            results[0]["is_lowest"] = True
            for r in results[1:]:
                r["is_lowest"] = False

            # 迷你图注入已移除——在大数据量或 SQLite 并发场景下可能挂死
            # 将来如需恢复，建议改为异步任务预计算 + 缓存

        return {"prices": results, "unit": target_unit_abbr}

    except Exception as e:
        import traceback
        print(f"[ERROR] 获取商品商家价格失败: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取商品商家价格失败: {str(e)}")


@router.get("/products/autocomplete")
@router.get("/products/autocomplete/")
def product_autocomplete(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="返回结果数量限制"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """商品自动完成搜索

    支持通过商品名称、商品别名或关联食材的别名搜索。
    返回结果包含匹配的别名信息，用于前端显示。

    例如：搜索"西"可以找到：
    - 商品"番茄"（别名"西红柿"匹配）
    - 商品"西瓜"（名称匹配）
    """
    try:
        search_lower = q.lower()

        # 查询所有活跃的商品，预加载关联的食材
        products = db.query(Product).options(
            joinedload(Product.ingredient)
        ).filter(Product.is_active == True).all()

        # 统计每个原料下的活跃商品数量（用于前端原料→商品择优）
        from collections import Counter
        ingredient_product_counts: dict[int, int] = Counter(
            p.ingredient_id for p in products if p.ingredient_id
        )

        results = []
        for product in products:
            matched_alias = None
            match_type = None

            # 检查商品名称是否匹配
            if search_lower in product.name.lower():
                match_type = "name"
            # 检查商品别名是否匹配
            elif product.aliases:
                for alias in product.aliases:
                    if search_lower in alias.lower():
                        matched_alias = alias
                        match_type = "alias"
                        break
            # 检查关联食材的名称是否匹配
            if not match_type and product.ingredient:
                if search_lower in product.ingredient.name.lower():
                    match_type = "ingredient_name"
                # 检查食材别名是否匹配
                elif product.ingredient.aliases:
                    for alias in product.ingredient.aliases:
                        if search_lower in alias.lower():
                            matched_alias = alias
                            match_type = "ingredient_alias"
                            break

            if match_type:
                results.append({
                    "id": product.id,
                    "name": product.name,
                    "brand": product.brand,
                    "ingredient_id": product.ingredient_id,
                    "ingredient_name": product.ingredient.name if product.ingredient else None,
                    "aliases": product.aliases or [],
                    "ingredient_aliases": product.ingredient.aliases if product.ingredient else [],
                    "match_type": match_type,
                    "matched_alias": matched_alias,
                    "created_at": product.created_at.isoformat() if product.created_at else None,
                    "ingredient_product_count": ingredient_product_counts.get(product.ingredient_id, 0)
                })

        # 按匹配类型排序：名称匹配 > 商品别名匹配 > 食材名称匹配 > 食材别名匹配
        match_order = {"name": 0, "alias": 1, "ingredient_name": 2, "ingredient_alias": 3}
        results.sort(key=lambda x: (match_order.get(x["match_type"], 9), x["name"]))

        return results[:limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"商品自动完成搜索失败: {str(e)}")


# ==================== 商品营养数据端点 ====================

@router.get("/products/entity/{product_id}/nutrition")
async def get_product_nutrition(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取商品的营养数据

    回退逻辑：
    1. 如果商品有 custom_nutrition_data，使用商品数据
    2. 如果商品的某项营养素未设置，从所属原料获取
    3. 如果原料也没有，使用层级关系回退
    """
    try:
        # 查询商品及其原料
        product = db.query(Product).options(
            joinedload(Product.ingredient)
        ).filter(Product.id == product_id, Product.is_active == True).first()

        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")

        if not product.ingredient:
            raise HTTPException(status_code=400, detail="商品未关联原料")

        ingredient = product.ingredient

        # 获取商品自定义营养数据
        product_nutrition = product.custom_nutrition_data or {}

        # 从原料获取营养数据
        ingredient_nutrition = _get_ingredient_nutrition_with_fallback(db, ingredient)

        # 合并营养数据（商品数据优先）
        merged_nutrition = _merge_nutrition_data(product_nutrition, ingredient_nutrition)

        return {
            "product_id": product.id,
            "product_name": product.name,
            "ingredient_id": ingredient.id,
            "ingredient_name": ingredient.name,
            "custom_nutrition_data": product.custom_nutrition_data,
            "nutrition": merged_nutrition,
            "source": "product" if product.custom_nutrition_data else "ingredient"
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[ERROR] 获取商品营养数据失败: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取商品营养数据失败: {str(e)}")


@router.put("/products/entity/{product_id}/nutrition")
async def update_product_nutrition(
    product_id: int,
    nutrition: Optional[dict] = Body(None, description="营养数据，传 null 清空自定义数据"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新/清空商品营养数据（分流：管理员直写 / 普通用户提议）。

    传 null / 空 dict 清除自定义营养数据，回退到继承原料数据。
    普通用户：有数据→manual 待审；无数据→补空 auto。

    请求体格式（非清空时）：
    {
        "core_nutrients": {
            "能量": {"value": 100, "unit": "kcal"},
            "蛋白质": {"value": 10, "unit": "g"}
        },
        "all_nutrients": {
            "energy": {"value": 100, "unit": "kcal"},
            "protein": {"value": 10, "unit": "g"}
        }
    }
    """
    try:
        product = db.query(Product).filter(
            Product.id == product_id,
            Product.is_active == True
        ).first()

        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")

        payload = {
            "custom_nutrition_data": nutrition,
            "custom_nutrition_source": "custom" if nutrition else None,
            "updated_by": current_user.id,
        }

        if current_user.is_admin:
            proposal_service.apply_as_admin(
                db,
                entity_type="product_nutrition",
                entity_id=product_id,
                action="update",
                payload=payload,
                admin=current_user,
            )
            db.commit()
            return {
                "message": "营养数据更新成功（管理员直写）",
                "custom_nutrition_data": nutrition,
            }

        has_data = bool(product.custom_nutrition_data)
        policy = "manual" if has_data else "auto_approve"
        p = proposal_service.submit(
            db,
            entity_type="product_nutrition",
            entity_id=product_id,
            action="update",
            payload=payload,
            proposer=current_user,
            policy_override=policy,
        )
        db.commit()
        if p.status == "applied":
            return {
                "message": "营养数据更新成功（补空自动通过）",
                "custom_nutrition_data": nutrition,
            }
        return {
            "message": f"营养数据更新提议已提交（status={p.status}，待管理员审核）",
            "custom_nutrition_data": product.custom_nutrition_data,  # 待审未变，返旧值
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        print(f"[ERROR] 更新商品营养数据失败: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"更新商品营养数据失败: {str(e)}")


def _get_ingredient_nutrition_with_fallback(db: Session, ingredient) -> dict:
    """
    获取原料的营养数据（包含层级关系回退）

    回退逻辑（与 NutritionCalculator.calculate_ingredient_nutrition 对齐）：
    1. 优先取自定义营养数据（source='custom'）
    2. 其次取已验证的营养数据（is_verified=True，覆盖 USDA 导入数据）
    3. 最后通过 nutrition_id 外键查找（保留作为额外回退）
    """
    from app.models.nutrition_data import NutritionData

    # 1. 获取最佳可用营养数据（custom > usda_import/usda_manual_match > 其他已验证）
    from app.models.mixins import NutritionMixin
    nutrition = NutritionMixin.get_best_nutrition_data(db, ingredient.id)
    if nutrition:
        return nutrition.nutrients

    # 3. 通过 nutrition_id 外键查找（额外回退）
    if ingredient.nutrition_id:
        linked_nutrition = db.query(NutritionData).filter(
            NutritionData.id == ingredient.nutrition_id
        ).first()

        if linked_nutrition:
            return linked_nutrition.nutrients

    # 无任何营养数据
    return {"core_nutrients": {}, "all_nutrients": {}}


def _merge_nutrition_data(product_nutrition: dict, ingredient_nutrition: dict) -> dict:
    """
    合并商品和原料的营养数据

    优先级：商品数据 > 原料数据
    """
    core_nutrients = {}
    all_nutrients = {}
    nutrient_details = {}

    # 先从原料获取基础数据
    if ingredient_nutrition.get("core_nutrients"):
        core_nutrients.update(ingredient_nutrition["core_nutrients"])
    if ingredient_nutrition.get("all_nutrients"):
        all_nutrients.update(ingredient_nutrition["all_nutrients"])
    if ingredient_nutrition.get("nutrient_details"):
        nutrient_details.update(ingredient_nutrition["nutrient_details"])

    # 商品数据覆盖原料数据
    if product_nutrition.get("core_nutrients"):
        core_nutrients.update(product_nutrition["core_nutrients"])
    if product_nutrition.get("all_nutrients"):
        all_nutrients.update(product_nutrition["all_nutrients"])
    if product_nutrition.get("nutrient_details"):
        nutrient_details.update(product_nutrition["nutrient_details"])

    return {
        "core_nutrients": core_nutrients,
        "all_nutrients": all_nutrients,
        "nutrient_details": nutrient_details
    }


@router.post("/products/entity/{product_id}/split-to-ingredient")
async def split_product_to_ingredient(
    product_id: int,
    new_name: Optional[str] = Body(None, embed=True, description="新原料名称，同名冲突时指定"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    将商品拆分为新的原料

    分流：管理员提交即执行 / 普通用户提交提议待审。
    逻辑：
    1. 如果商品是当前原料的唯一活跃商品，不允许拆分
    2. 创建同名原料（冲突时需要指定 new_name）
    3. 将商品的营养数据 mixin 写入新原料
    4. 商品关联到新原料，清空商品的自定义营养数据
    """
    # 业务校验（通用：不受审核状态影响）
    product = db.query(Product).options(
        joinedload(Product.ingredient)
    ).filter(
        Product.id == product_id,
        Product.is_active == True
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    if not product.ingredient_id:
        raise HTTPException(status_code=400, detail="商品未关联原料")

    current_ingredient = product.ingredient

    # 唯一商品检查
    active_product_count = db.query(Product).filter(
        Product.ingredient_id == current_ingredient.id,
        Product.is_active == True
    ).count()
    if active_product_count <= 1:
        raise HTTPException(
            status_code=400,
            detail="该商品是当前原料的唯一商品，无法拆分。请先为该原料添加其他商品。"
        )

    # 同名冲突检查
    ingredient_name = (new_name or product.name).strip()
    if not ingredient_name:
        raise HTTPException(status_code=400, detail="原料名称不能为空")
    existing_ingredient = db.query(Ingredient).filter(
        Ingredient.name == ingredient_name,
        Ingredient.is_active == True
    ).first()
    if existing_ingredient:
        if existing_ingredient.id == current_ingredient.id:
            raise HTTPException(
                status_code=409,
                detail=f"原料「{ingredient_name}」与当前关联原料同名，请指定不同的新原料名称。"
            )
        raise HTTPException(
            status_code=409,
            detail=f"原料「{ingredient_name}」已存在（ID: {existing_ingredient.id}），请指定不同的名称。"
        )

    payload = {"new_name": new_name} if new_name else {}

    # 分流：管理员直写 / 普通用户提议
    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="product_split", entity_id=product_id,
            action="split", payload=payload, admin=current_user,
        )
        db.commit()

        # 重新读取刷新后的商品
        db.refresh(product)
        return {
            "message": f"商品已拆分为原料「{ingredient_name}」",
            "ingredient_id": product.ingredient_id,
            "ingredient_name": ingredient_name,
        }

    p = proposal_service.submit(
        db, entity_type="product_split", entity_id=product_id,
        action="split", payload=payload, proposer=current_user,
    )
    db.commit()
    return {
        "message": f"拆分提议已提交，待管理员审核（proposal_id={p.id}）",
        "proposal_id": p.id,
    }


@router.post("/products/entity/{product_id}/merge-into/{target_product_id}")
def merge_product_into(
    product_id: int,
    target_product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    将商品合并到同一原料下的另一个商品

    分流：管理员提交即执行 / 普通用户提交提议待审。
    逻辑：
    1. 源商品和目标商品必须在同一原料下
    2. 源商品的价格记录迁移到目标商品
    3. 源商品软删除
    """
    # 业务校验（通用）
    source_product = db.query(Product).filter(
        Product.id == product_id,
        Product.is_active == True
    ).first()
    if not source_product:
        raise HTTPException(status_code=404, detail="源商品不存在")

    target_product = db.query(Product).filter(
        Product.id == target_product_id,
        Product.is_active == True
    ).first()
    if not target_product:
        raise HTTPException(status_code=404, detail="目标商品不存在")

    # 校验同一原料
    if source_product.ingredient_id != target_product.ingredient_id:
        raise HTTPException(
            status_code=400,
            detail="只能合并同一原料下的商品"
        )
    if source_product.id == target_product.id:
        raise HTTPException(status_code=400, detail="不能将商品合并到自身")

    payload = {"target_product_id": target_product_id}

    # 分流：管理员直写 / 普通用户提议
    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="product_merge", entity_id=product_id,
            action="merge", payload=payload, admin=current_user,
        )
        db.commit()

        # 读取合并后数据
        price_record_count = db.query(ProductRecord).filter(
            ProductRecord.product_id == target_product_id,
            ProductRecord.is_active == True
        ).count()

        return {
            "message": f"已合并到「{target_product.name}」",
            "target_id": target_product.id,
            "target_name": target_product.name,
            "price_record_count": price_record_count,
        }

    p = proposal_service.submit(
        db, entity_type="product_merge", entity_id=product_id,
        action="merge", payload=payload, proposer=current_user,
    )
    db.commit()
    return {
        "message": f"合并提议已提交，待管理员审核（proposal_id={p.id}）",
        "proposal_id": p.id,
    }


@router.post("/products/entity/{product_id}/add-import-alias")
def add_import_alias(
    product_id: int,
    body: ImportAliasRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """粘贴导入时将商品名添加为别名

    规则：
    - 商品与原料同名 → 别名加到原料
    - 原料下唯一商品 → 别名加到原料
    - 否则 → 别名加到商品
    """
    alias_name = body.name.strip()
    if not alias_name:
        raise HTTPException(status_code=400, detail="name is required")

    product = db.query(Product).filter(
        Product.id == product_id, Product.is_active == True
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    ingredient = product.ingredient
    if not ingredient or not ingredient.is_active:
        raise HTTPException(status_code=404, detail="关联原料不存在")

    # 判断别名加到商品还是原料
    same_name_as_ingredient = (product.name == ingredient.name)
    sibling_count = db.query(Product).filter(
        Product.ingredient_id == ingredient.id,
        Product.is_active == True,
        Product.id != product_id
    ).count()
    only_product = (sibling_count == 0)

    if same_name_as_ingredient or only_product:
        target = ingredient
        target_type = "ingredient"
    else:
        target = product
        target_type = "product"

    target_name = target.name
    aliases = list(target.aliases or [])  # 拷贝，避免直接操作 ORM 追踪对象

    added = False
    if alias_name != target_name and alias_name not in aliases:
        aliases.append(alias_name)
        # 直接用数据库级 UPDATE 绕过 SQLAlchemy JSON 列变更检测问题
        if target_type == "ingredient":
            db.query(Ingredient).filter(Ingredient.id == target.id).update(
                {"aliases": aliases, "updated_by": current_user.id},
                synchronize_session="fetch"
            )
        else:
            db.query(Product).filter(Product.id == target.id).update(
                {"aliases": aliases, "updated_by": current_user.id},
                synchronize_session="fetch"
            )
        db.commit()
        added = True

    return {
        "target": target_type,
        "target_id": target.id,
        "target_name": target_name,
        "added": added,
        "aliases": aliases
    }
