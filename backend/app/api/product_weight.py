"""商品价格权重的用户覆盖 API（个人偏好，不走审核）。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.product_entity import Product
from app.models.user_product_weight_override import UserProductWeightOverride
from app.schemas.product_weight import (
    ProductWeightOverrideCreate,
    ProductWeightOverrideResponse,
    EffectiveWeightResponse,
)
from app.services.ingredient_price_service import _DEFAULT_WEIGHT

router = APIRouter(tags=["product-weight"])


@router.get("/products/{product_id}/my-weight", response_model=EffectiveWeightResponse)
def get_my_weight(product_id: int, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    """获取该商品对当前用户的生效权重（覆盖 > 全局）。"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "商品不存在")
    ov = db.query(UserProductWeightOverride).filter(
        UserProductWeightOverride.user_id == current_user.id,
        UserProductWeightOverride.product_id == product_id,
        UserProductWeightOverride.is_active == True,  # noqa: E712
    ).first()
    gw = product.price_weight if product.price_weight is not None else _DEFAULT_WEIGHT
    if ov is not None:
        return EffectiveWeightResponse(
            product_id=product_id, effective_weight=ov.weight,
            global_weight=gw, override_weight=ov.weight, source="override",
        )
    return EffectiveWeightResponse(
        product_id=product_id, effective_weight=gw,
        global_weight=gw, override_weight=None, source="global",
    )


@router.put("/products/{product_id}/my-weight", response_model=ProductWeightOverrideResponse)
@router.put("/products/{product_id}/my-weight/", response_model=ProductWeightOverrideResponse)
def set_my_weight(product_id: int, body: ProductWeightOverrideCreate,
                  db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    """设置/更新当前用户对该商品的权重覆盖。"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "商品不存在")
    existing = db.query(UserProductWeightOverride).filter(
        UserProductWeightOverride.user_id == current_user.id,
        UserProductWeightOverride.product_id == product_id,
    ).first()
    if existing:
        existing.weight = body.weight
        existing.is_active = True
        existing.updated_by = current_user.id
        db.commit()
        db.refresh(existing)
        return existing
    obj = UserProductWeightOverride(
        user_id=current_user.id, product_id=product_id,
        weight=body.weight, created_by=current_user.id, updated_by=current_user.id,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/products/{product_id}/my-weight")
@router.delete("/products/{product_id}/my-weight/")
def delete_my_weight(product_id: int, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    """删除当前用户对该商品的权重覆盖（回退到全局）。"""
    existing = db.query(UserProductWeightOverride).filter(
        UserProductWeightOverride.user_id == current_user.id,
        UserProductWeightOverride.product_id == product_id,
    ).first()
    if not existing:
        raise HTTPException(404, "覆盖不存在")
    existing.is_active = False
    existing.updated_by = current_user.id
    db.commit()
    return {"message": "已删除覆盖，回退到全局权重"}
