# backend/app/api/usda.py
"""USDA 用户路由：搜索 / 详情 / 匹配写入（原料/商品）。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.auth import UserResponse
from app.schemas.usda import UsdaSearchItem, UsdaFoodDetail, UsdaNutrientItem, UsdaMatchRequest
from app.models.usda import UsdaFood, UsdaFoodNutrient
from app.services.usda.index_manager import get_usda_index
from app.services.usda.matcher import match_ingredient, match_product

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
    """把 USDA 食材营养数据写入指定原料。

    TODO(权限): 现有 ingredient 写端点（ingredient_extended.py / products_entity.py）
    均只校验 `get_current_user`（登录即可），未做 owner/admin 校验。待项目引入
    统一的所有者权限依赖后，替换此处 `get_current_user`。
    """
    return match_ingredient(db, ingredient_id, body.fdc_id)


@router.post("/match/product/{product_id}")
async def match_product_endpoint(
    product_id: int,
    body: UsdaMatchRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """把 USDA 食材营养数据写入指定商品的 custom_nutrition_data。

    TODO(权限): 同 match_ingredient_endpoint，待统一所有者权限依赖后替换。
    """
    return match_product(db, product_id, body.fdc_id)
