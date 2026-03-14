"""商品实体 API 路由"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.product_entity import Product
from app.models.product_barcode import ProductBarcode
from app.models.product import ProductRecord
from app.schemas.product_entity import (
    ProductCreate, ProductUpdate, ProductResponse, ProductWithDetails,
    ProductBarcodeCreate, ProductBarcodeUpdate, ProductBarcodeResponse
)
from app.schemas.common import PaginatedResponse
from app.utils.database_helpers import serialize_tags, deserialize_tags

router = APIRouter(tags=["products_entity"])


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
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db)
):
    """获取商品列表（分页）"""
    query = db.query(Product).filter(Product.is_active == True)

    if ingredient_id:
        query = query.filter(Product.ingredient_id == ingredient_id)

    if search:
        query = query.filter(Product.name.contains(search))

    total = query.count()
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
            "created_at": product.created_at.isoformat() if product.created_at else None,
            "updated_at": product.updated_at.isoformat() if product.updated_at else None,
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
def get_product(product_id: int, db: Session = Depends(get_db)):
    """获取商品详情"""
    product = db.query(Product).filter(Product.id == product_id, Product.is_active == True).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 反序列化 tags
    if product.tags:
        product.tags = deserialize_tags(product.tags)
    else:
        product.tags = []

    # 获取最新价格记录
    latest_price_record = db.query(ProductRecord).filter(
        ProductRecord.product_id == product_id
    ).order_by(desc(ProductRecord.recorded_at)).first()

    latest_price = float(latest_price_record.price) if latest_price_record else None
    latest_price_date = latest_price_record.recorded_at if latest_price_record else None

    # 构建详细响应
    response = ProductWithDetails(
        **product.__dict__,
        ingredient_name=product.ingredient.name if product.ingredient else None,
        latest_price=latest_price,
        latest_price_date=latest_price_date
    )
    return response


@router.put("/products/entity/{product_id}", response_model=ProductResponse)
@router.put("/products/entity/{product_id}/", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新商品"""
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product_update.model_dump(exclude_unset=True)

    # 检查条码唯一性
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

    for field, value in update_data.items():
        setattr(db_product, field, value)

    db_product.updated_by = current_user.id
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


@router.delete("/products/entity/{product_id}")
@router.delete("/products/entity/{product_id}/")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """软删除商品"""
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    db_product.is_active = False
    db_product.updated_by = current_user.id
    db.commit()
    return {"message": "Product deleted successfully"}


# ==================== 条码管理端点 ====================

@router.post("/products/entity/{product_id}/barcodes", response_model=ProductBarcodeResponse)
def add_product_barcode(
    product_id: int,
    barcode: ProductBarcodeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    db: Session = Depends(get_db)
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
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
):
    """删除条码（软删除）"""
    barcode = db.query(ProductBarcode).filter(ProductBarcode.id == barcode_id).first()
    if not barcode:
        raise HTTPException(status_code=404, detail="Barcode not found")

    barcode.is_active = False
    barcode.updated_by = current_user.id
    db.commit()

    return {"message": "Barcode deleted successfully"}
