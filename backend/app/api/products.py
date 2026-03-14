from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
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
from app.services.unit_matcher import UnitMatcher

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
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取商品记录列表（分页）"""
    query = db.query(ProductRecord).options(
        joinedload(ProductRecord.original_unit),
        joinedload(ProductRecord.standard_unit),
        joinedload(ProductRecord.merchant)
    ).filter(ProductRecord.user_id == current_user.id)

    # 优先使用 product_id 过滤
    if product_id:
        query = query.filter(ProductRecord.product_id == product_id)
    # 然后使用search参数（优先）或product_name参数进行过滤
    else:
        search_term = search or product_name
        if search_term:
            query = query.filter(ProductRecord.product_name.contains(search_term))

    # 添加日期范围过滤
    if start_date:
        query = query.filter(ProductRecord.recorded_at >= start_date)
    if end_date:
        query = query.filter(ProductRecord.recorded_at <= end_date)

    total = query.count()
    records = query.order_by(ProductRecord.recorded_at.desc()).offset(skip).limit(limit).all()
    page = skip // limit + 1

    # 手动构造响应列表，将 Unit 对象转换为字符串
    return PaginatedResponse.create(
        items=[
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
        ],
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
