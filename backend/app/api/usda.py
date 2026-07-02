# backend/app/api/usda.py
"""USDA 用户路由：搜索 / 详情 / 匹配写入（原料/商品）。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user
from app.schemas.auth import UserResponse
from app.schemas.usda import UsdaSearchItem, UsdaFoodDetail, UsdaNutrientItem, UsdaMatchRequest
from app.models.usda import UsdaFood, UsdaFoodNutrient
from app.services.usda.index_manager import get_usda_index

router = APIRouter()


@router.get("/search", response_model=list[UsdaSearchItem])
async def search_usda(
    q: str = "",
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    if not q.strip():
        return []
    index = get_usda_index()
    hits = index.search(q, limit=limit)
    if not hits:
        return []
    fdc_ids = [h["fdc_id"] for h in hits]
    score_map = {h["fdc_id"]: h["score"] for h in hits}
    rows = db.query(UsdaFood).filter(UsdaFood.fdc_id.in_(fdc_ids)).all()
    counts = dict(
        db.query(UsdaFoodNutrient.fdc_id, func.count(UsdaFoodNutrient.id))
        .filter(UsdaFoodNutrient.fdc_id.in_(fdc_ids))
        .group_by(UsdaFoodNutrient.fdc_id)
        .all()
    )
    out = [
        UsdaSearchItem(
            fdc_id=r.fdc_id,
            description=r.description,
            description_zh=r.description_zh,
            data_type=r.data_type,
            nutrient_count=counts.get(r.fdc_id, 0),
            score=score_map.get(r.fdc_id, 0),
        )
        for r in rows
    ]
    out.sort(key=lambda x: -x.score)
    return out


@router.get("/preview-nutrition")
async def preview_usda_nutrition(
    fdc_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """按 fdc_id 预览 USDA 营养素（只读，供审核台 NutritionDiff 渲染新值）。

    返回三层结构（core_nutrients / all_nutrients / nutrient_details），
    与 match_ingredient 写入 NutritionData.nutrients 的结构一致。
    """
    from app.services.usda.matcher import build_usda_nutrients_by_fdc
    return build_usda_nutrients_by_fdc(db, fdc_id)


@router.get("/{fdc_id}", response_model=UsdaFoodDetail)
async def get_usda_food(
    fdc_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    food = db.query(UsdaFood).filter(UsdaFood.fdc_id == fdc_id).first()
    if not food:
        raise HTTPException(status_code=404, detail="USDA 食材不存在")
    nutrients = (
        db.query(UsdaFoodNutrient).filter(UsdaFoodNutrient.fdc_id == fdc_id).all()
    )
    return UsdaFoodDetail(
        fdc_id=food.fdc_id,
        description=food.description,
        description_zh=food.description_zh,
        data_type=food.data_type,
        nutrients=[
            UsdaNutrientItem(
                name=n.name,
                name_zh=n.name_zh,
                amount=n.amount,
                unit_name=n.unit_name,
            )
            for n in nutrients
        ],
    )


@router.post("/match/ingredient/{ingredient_id}")
async def match_ingredient_endpoint(
    ingredient_id: int,
    body: UsdaMatchRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """把 USDA 食材营养数据写入指定原料（分流：管理员直写 / 普通用户提议）。

    普通用户：有数据→manual 待审；无数据→补空 auto_approve 立即生效。
    """
    from app.models.nutrition import Ingredient
    from app.models.nutrition_data import NutritionData
    from app.services.proposals import service as proposal_service

    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="原料不存在")

    payload = {"fdc_id": body.fdc_id}

    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="usda_ingredient_match", entity_id=ingredient_id,
            action="create", payload=payload, admin=current_user,
        )
        db.commit()
        return {"ingredient_id": ingredient_id, "fdc_id": body.fdc_id, "message": "USDA 匹配成功（管理员直写）"}

    has_data = db.query(NutritionData).filter(
        NutritionData.ingredient_id == ingredient_id).count() > 0
    policy = "manual" if has_data else "auto_approve"
    p = proposal_service.submit(
        db, entity_type="usda_ingredient_match", entity_id=ingredient_id,
        action="create", payload=payload, proposer=current_user, policy_override=policy,
    )
    db.commit()
    if p.status == "applied":
        return {"ingredient_id": ingredient_id, "fdc_id": body.fdc_id, "message": "USDA 匹配成功（补空自动通过）"}
    return {"ingredient_id": ingredient_id, "fdc_id": body.fdc_id, "message": f"USDA 匹配提议已提交（status={p.status}，待管理员审核）"}


@router.post("/match/product/{product_id}")
async def match_product_endpoint(
    product_id: int,
    body: UsdaMatchRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """把 USDA 食材营养数据写入指定商品的 custom_nutrition_data（分流：管理员直写 / 普通用户提议）。

    普通用户：商品有 custom_nutrition_data→manual 待审；无数据→补空 auto_approve 立即生效。
    """
    from app.models.product_entity import Product
    from app.services.proposals import service as proposal_service

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    payload = {"fdc_id": body.fdc_id}

    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="usda_product_match", entity_id=product_id,
            action="create", payload=payload, admin=current_user,
        )
        db.commit()
        return {"product_id": product_id, "fdc_id": body.fdc_id, "message": "USDA 匹配成功（管理员直写）"}

    has_data = bool(product.custom_nutrition_data)
    policy = "manual" if has_data else "auto_approve"
    p = proposal_service.submit(
        db, entity_type="usda_product_match", entity_id=product_id,
        action="create", payload=payload, proposer=current_user, policy_override=policy,
    )
    db.commit()
    if p.status == "applied":
        return {"product_id": product_id, "fdc_id": body.fdc_id, "message": "USDA 匹配成功（补空自动通过）"}
    return {"product_id": product_id, "fdc_id": body.fdc_id, "message": f"USDA 匹配提议已提交（status={p.status}，待管理员审核）"}
