from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.product import ProductRecord
from app.schemas.product import (
    ProductRecordCreate,
    ProductRecordResponse,
    ProductHistoryResponse
)
from app.utils.unit_converter import convert_to_standard

router = APIRouter()


@router.post("/", response_model=ProductRecordResponse)
async def create_product_record(
    record: ProductRecordCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建商品记录"""
    # 获取当天汇率
    exchange_rate = 1.0  # TODO: 从汇率服务获取

    # 单位转换
    standard_quantity, standard_unit = convert_to_standard(
        record.original_quantity,
        record.original_unit
    )

    # 创建记录
    db_record = ProductRecord(
        user_id=current_user.id,
        product_name=record.product_name,
        location_id=record.location_id,
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
