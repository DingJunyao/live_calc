from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.nutrition import (
    NutritionDataResponse,
    NutritionMatchResponse,
    NutritionCorrectRequest
)
from app.services.nutrition_service import (
    search_nutrition,
    match_ingredient,
    correct_mapping
)

router = APIRouter()


@router.get("/search", response_model=List[NutritionDataResponse])
async def search_nutrition_data(
    query: str = Query(..., min_length=1),
    fuzzy: bool = Query(False),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """搜索营养数据"""
    try:
        results = await search_nutrition(query, fuzzy=fuzzy, limit=limit, db=db)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索营养数据失败: {str(e)}")


@router.post("/match", response_model=NutritionMatchResponse)
async def match_ingredient_nutrition(
    ingredient_name: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """匹配食材到营养数据"""
    try:
        matches = await match_ingredient(ingredient_name, db=db)
        return NutritionMatchResponse(matches=matches)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匹配食材失败: {str(e)}")


@router.post("/correct")
async def correct_nutrition_mapping(
    request: NutritionCorrectRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """更正映射"""
    try:
        success = await correct_mapping(
            request.ingredient_name,
            request.nutrition_id,
            db=db
        )
        if not success:
            raise HTTPException(status_code=404, detail="更正失败")
        return {"success": True, "message": "更正成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更正失败: {str(e)}")
