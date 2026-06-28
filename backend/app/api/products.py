# 价格记录 API - 支持通过食材别名搜索（最后修改: 2026-03-27 23:30）
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, text, or_, and_
from typing import List, Optional
from datetime import datetime, timedelta
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
from app.utils.database_helpers import json_text_contains
from app.services.unit_matcher import UnitMatcher
from app.services.unit_conversion_service import UnitConversionService

router = APIRouter()


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


def _get_or_create_product(
    db: Session, product_name: str, current_user, ingredient_id: Optional[int] = None
) -> Product:
    """获取或创建商品

    指定 ingredient_id 时，在该原料下创建商品（用于挂靠已有原料场景）；
    否则获取或创建同名原料并在其下创建同名商品。
    注意：若已存在同名激活商品，直接复用并忽略 ingredient_id。
    """
    # 首先尝试查找已存在的同名商品（处于激活状态）
    product = db.query(Product).filter(
        Product.name == product_name,
        Product.is_active == True
    ).first()

    if product:
        return product

    # 确定挂靠的原料（用 is not None，避免把 0 误判为未提供）
    if ingredient_id is not None:
        ingredient = db.query(Ingredient).filter(
            Ingredient.id == ingredient_id,
            Ingredient.is_active == True
        ).first()
        if not ingredient:
            raise HTTPException(
                status_code=404,
                detail=f"原料ID {ingredient_id} 不存在"
            )
    else:
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

        # 单位转换：优先使用新的 UnitConversionService，回退到旧转换器
        standard_quantity = None
        standard_unit_obj = None

        if original_unit_obj:
            conversion_service = UnitConversionService(db)
            # 尝试转换为 g（质量的标准显示单位）
            result = conversion_service.convert(
                Decimal(str(record.original_quantity)),
                original_unit_obj.abbreviation,
                "g",
                "product" if record.product_id else None,
                record.product_id,
            )
            if result:
                standard_quantity, _ = result
                g_unit = matcher.match_or_create_unit("g")
                if g_unit:
                    standard_unit_obj = g_unit

        # 回退到旧转换器
        if standard_quantity is None:
            sq, su_str = convert_to_standard(
                record.original_quantity,
                record.original_unit
            )
            standard_quantity = sq
            standard_unit_obj = matcher.match_or_create_unit(su_str)

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
            product = _get_or_create_product(db, record.product_name, current_user, record.ingredient_id)
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
        # P2 共享转型：写入时增量重算去标识公开聚合汇总（不含 user_id/record_type）
        from app.services.price_aggregator import recompute_summary
        recompute_summary(db, product_id=product_id, merchant_id=db_record.merchant_id)
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
    merchant_ids: Optional[str] = Query(None, description="商家ID列表，逗号分隔"),
    record_types: Optional[str] = Query(None, description="记录类型列表，逗号分隔（purchase,price）"),
    ingredient_category_ids: Optional[str] = Query(None, description="原料分类ID列表，逗号分隔"),
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
        rc_filter = [ProductRecord.is_active == True]
        if not ingredient_id and not product_id:
            rc_filter.append(ProductRecord.user_id == current_user.id)
        record_counts = db.query(
            ProductRecord.product_id,
            func.count(ProductRecord.id).label('record_count')
        ).filter(*rc_filter)

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
                # 搜索商品名称、商品别名或关联食材的别名
                record_counts = record_counts.join(ProductRecord.product).join(
                    Product.ingredient
                ).filter(
                    or_(
                        ProductRecord.product_name.contains(search_term),
                        json_text_contains(Product.aliases, search_term),
                        Ingredient.name.contains(search_term),
                        json_text_contains(Ingredient.aliases, search_term)
                    )
                )

        # 添加日期范围过滤
        if start_date:
            if start_date.tzinfo:
                start_date = datetime.fromtimestamp(start_date.timestamp())
            record_counts = record_counts.filter(ProductRecord.recorded_at >= start_date)
        if end_date:
            if end_date.tzinfo:
                end_date = datetime.fromtimestamp(end_date.timestamp())
            record_counts = record_counts.filter(ProductRecord.recorded_at <= end_date)

        # 多选商家筛选
        if merchant_ids:
            ids = [int(x.strip()) for x in merchant_ids.split(',') if x.strip()]
            if ids:
                record_counts = record_counts.filter(ProductRecord.merchant_id.in_(ids))

        # 多选记录类型筛选
        if record_types:
            types_list = [x.strip() for x in record_types.split(',') if x.strip()]
            if types_list:
                record_counts = record_counts.filter(ProductRecord.record_type.in_(types_list))

        # 跨表：按原料分类筛选
        if ingredient_category_ids:
            cat_ids = [int(x.strip()) for x in ingredient_category_ids.split(',') if x.strip()]
            if cat_ids:
                record_counts = record_counts.join(ProductRecord.product).join(
                    Product.ingredient
                ).filter(Ingredient.category_id.in_(cat_ids))

        record_counts = record_counts.group_by(ProductRecord.product_id).subquery()

        # 主查询：获取记录，并关联商品的记录数量
        query = db.query(ProductRecord).outerjoin(
            record_counts, ProductRecord.product_id == record_counts.c.product_id
        ).options(
            joinedload(ProductRecord.original_unit),
            joinedload(ProductRecord.standard_unit),
            joinedload(ProductRecord.merchant)
        )
        if not ingredient_id and not product_id:
            query = query.filter(ProductRecord.user_id == current_user.id)

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
                # 搜索商品名称、商品别名或关联食材的别名
                query = query.join(ProductRecord.product).join(
                    Product.ingredient
                ).filter(
                    or_(
                        ProductRecord.product_name.contains(search_term),
                        json_text_contains(Product.aliases, search_term),
                        Ingredient.name.contains(search_term),
                        json_text_contains(Ingredient.aliases, search_term)
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

        # 多选商家筛选
        if merchant_ids:
            ids = [int(x.strip()) for x in merchant_ids.split(',') if x.strip()]
            if ids:
                query = query.filter(ProductRecord.merchant_id.in_(ids))

        # 多选记录类型筛选
        if record_types:
            types_list = [x.strip() for x in record_types.split(',') if x.strip()]
            if types_list:
                query = query.filter(ProductRecord.record_type.in_(types_list))

        # 跨表：按原料分类筛选
        if ingredient_category_ids:
            cat_ids = [int(x.strip()) for x in ingredient_category_ids.split(',') if x.strip()]
            if cat_ids:
                query = query.join(ProductRecord.product).join(
                    Product.ingredient
                ).filter(Ingredient.category_id.in_(cat_ids))

        total = query.count()

        # 按商品的价格记录数量排序，然后按记录时间排序（为了稳定性）
        records = query.order_by(record_counts.c.record_count.desc(), ProductRecord.recorded_at.desc()).offset(skip).limit(limit).all()
    else:
        # 使用原有逻辑
        query = db.query(ProductRecord).options(
            joinedload(ProductRecord.original_unit),
            joinedload(ProductRecord.standard_unit),
            joinedload(ProductRecord.merchant)
        ).filter(
            ProductRecord.is_active == True
        )
        if not ingredient_id and not product_id:
            query = query.filter(ProductRecord.user_id == current_user.id)

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
                # 搜索商品名称、商品别名或关联食材的别名
                query = query.join(ProductRecord.product).join(
                    Product.ingredient
                ).filter(
                    or_(
                        ProductRecord.product_name.contains(search_term),
                        json_text_contains(Product.aliases, search_term),
                        Ingredient.name.contains(search_term),
                        json_text_contains(Ingredient.aliases, search_term)
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

        # 多选商家筛选
        if merchant_ids:
            ids = [int(x.strip()) for x in merchant_ids.split(',') if x.strip()]
            if ids:
                query = query.filter(ProductRecord.merchant_id.in_(ids))

        # 多选记录类型筛选
        if record_types:
            types_list = [x.strip() for x in record_types.split(',') if x.strip()]
            if types_list:
                query = query.filter(ProductRecord.record_type.in_(types_list))

        # 跨表：按原料分类筛选（使用 has() 避免重复 join）
        if ingredient_category_ids:
            cat_ids = [int(x.strip()) for x in ingredient_category_ids.split(',') if x.strip()]
            if cat_ids:
                query = query.filter(
                    ProductRecord.product.has(
                        Product.ingredient.has(
                            Ingredient.category_id.in_(cat_ids)
                        )
                    )
                )

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
            convert_result = unit_service.convert(
                original_quantity,
                original_unit_abbr,
                target_unit,
            )

            if convert_result is not None:
                # 转换成功，使用转换后的数量和目标单位
                display_quantity, _ = convert_result
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
                record_type=None if ingredient_id else record.record_type,
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
            ProductRecord.is_active == True
        ).first()

        if not db_record:
            raise HTTPException(status_code=404, detail="价格记录不存在")
        if db_record.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="无权修改此价格记录")

        # 更新单位（如果需要）
        if record.original_unit:
            matcher = UnitMatcher(db)
            original_unit_obj = matcher.match_or_create_unit(record.original_unit)
        else:
            original_unit_obj = db_record.original_unit

        # 单位转换：优先使用新的 UnitConversionService
        if record.original_quantity and record.original_unit:
            standard_quantity = None
            standard_unit_obj = None
            if original_unit_obj:
                conversion_service = UnitConversionService(db)
                result = conversion_service.convert(
                    Decimal(str(record.original_quantity)),
                    original_unit_obj.abbreviation,
                    "g",
                    "product" if db_record.product_id else None,
                    db_record.product_id,
                )
                if result:
                    standard_quantity, _ = result
                    g_unit = matcher.match_or_create_unit("g")
                    if g_unit:
                        standard_unit_obj = g_unit
            if standard_quantity is None:
                sq, su_str = convert_to_standard(
                    record.original_quantity,
                    record.original_unit
                )
                standard_quantity = sq
                standard_unit_obj = matcher.match_or_create_unit(su_str)
        else:
            standard_quantity = db_record.standard_quantity
            standard_unit_obj = db_record.standard_unit

        # 更新字段
        update_data = record.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key not in ['original_unit', 'original_quantity']:  # 单位需要特殊处理
                setattr(db_record, key, value)

        # 更新数量和单位相关字段（original_quantity 被 exclude 跳过，需单独赋值）
        if record.original_quantity is not None:
            db_record.original_quantity = record.original_quantity
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
    """软删除价格记录

    管理员可删除任意记录，普通用户只能删除自己的记录。
    """
    try:
        db_record = db.query(ProductRecord).filter(
            ProductRecord.id == record_id,
            ProductRecord.is_active == True
        ).first()

        if not db_record:
            raise HTTPException(status_code=404, detail="价格记录不存在")
        if db_record.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="无权删除此价格记录")

        db_record.is_active = False
        db.commit()
        return {"message": "价格记录已删除"}
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
            record_type=None,
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

