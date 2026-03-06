from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.product import ProductRecord
from app.models.product_entity import Product
from app.models.nutrition import Ingredient
from app.schemas.product import (
    ProductRecordCreate,
    ProductRecordResponse,
    ProductHistoryResponse
)
from app.utils.unit_converter import convert_to_standard

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

        # 单位转换
        standard_quantity, standard_unit = convert_to_standard(
            record.original_quantity,
            record.original_unit
        )

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
            original_unit=record.original_unit,
            standard_quantity=standard_quantity,
            standard_unit=standard_unit,
            record_type=record.record_type,
            exchange_rate=exchange_rate,
            notes=record.notes
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)

        return db_record
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"创建记录失败: {str(e)}"
        )


@router.get("", response_model=List[ProductRecordResponse])
@router.get("/", response_model=List[ProductRecordResponse])
async def get_product_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    product_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取商品记录列表"""
    query = db.query(ProductRecord).filter(ProductRecord.user_id == current_user.id)

    if product_name:
        query = query.filter(ProductRecord.product_name.contains(product_name))

    records = query.order_by(ProductRecord.recorded_at.desc()).offset(skip).limit(limit).all()
    return records


@router.get("/{record_id}", response_model=ProductRecordResponse)
async def get_product_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取商品记录详情"""
    record = db.query(ProductRecord).filter(
        ProductRecord.id == record_id,
        ProductRecord.user_id == current_user.id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return record


@router.get("/history/{product_name}", response_model=ProductHistoryResponse)
async def get_product_history(
    product_name: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取商品历史价格"""
    records = db.query(ProductRecord).filter(
        ProductRecord.user_id == current_user.id,
        ProductRecord.product_name == product_name
    ).order_by(ProductRecord.recorded_at.desc()).all()

    return ProductHistoryResponse(
        product_name=product_name,
        records=records
    )
