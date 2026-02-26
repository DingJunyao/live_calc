from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.nutrition import Ingredient
from app.schemas.nutrition import (
    NutritionDataResponse,
    NutritionMatchResponse,
    NutritionCorrectRequest
)

router = APIRouter()


@router.get("/ingredients", response_model=List[dict])
async def get_ingredients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: str = Query(None, alias="q"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取原料列表"""
    try:
        query = db.query(Ingredient)

        if search:
            query = query.filter(Ingredient.name.contains(search))

        ingredients = query.offset(skip).limit(limit).all()

        return [{
            "id": ing.id,
            "name": ing.name,
            "aliases": ing.aliases or [],
            "created_at": ing.created_at
        } for ing in ingredients]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取原料列表失败: {str(e)}")


@router.get("/ingredients/{ingredient_id}", response_model=dict)
async def get_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取原料详情"""
    try:
        ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="原料不存在")

        return {
            "id": ingredient.id,
            "name": ingredient.name,
            "aliases": ingredient.aliases or [],
            "created_at": ingredient.created_at
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取原料详情失败: {str(e)}")


@router.post("/ingredients", response_model=dict)
async def create_ingredient(
    name: str = Query(..., min_length=1),
    aliases: str = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建原料"""
    try:
        # 检查原料是否已存在
        existing = db.query(Ingredient).filter(Ingredient.name == name).first()
        if existing:
            raise HTTPException(status_code=400, detail="原料已存在")

        # 解析别名
        aliases_list = []
        if aliases:
            aliases_list = [alias.strip() for alias in aliases.split(',') if alias.strip()]

        new_ingredient = Ingredient(
            name=name,
            aliases=aliases_list
        )
        db.add(new_ingredient)
        db.commit()
        db.refresh(new_ingredient)

        return {
            "id": new_ingredient.id,
            "name": new_ingredient.name,
            "aliases": new_ingredient.aliases or [],
            "created_at": new_ingredient.created_at
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建原料失败: {str(e)}")


@router.put("/ingredients/{ingredient_id}", response_model=dict)
async def update_ingredient(
    ingredient_id: int,
    name: str = Query(None),
    aliases: str = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """更新原料"""
    try:
        ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="原料不存在")

        # 如果提供了新的名字并且与原名不同，检查是否已存在
        if name and name != ingredient.name:
            existing = db.query(Ingredient).filter(Ingredient.name == name).first()
            if existing:
                raise HTTPException(status_code=400, detail="原料已存在")
            ingredient.name = name

        # 更新别名
        if aliases is not None:
            aliases_list = [alias.strip() for alias in aliases.split(',') if alias.strip()]
            ingredient.aliases = aliases_list

        db.commit()
        db.refresh(ingredient)

        return {
            "id": ingredient.id,
            "name": ingredient.name,
            "aliases": ingredient.aliases or [],
            "created_at": ingredient.created_at
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新原料失败: {str(e)}")


@router.delete("/ingredients/{ingredient_id}")
async def delete_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """删除原料"""
    try:
        ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="原料不存在")

        db.delete(ingredient)
        db.commit()

        return {"message": "原料删除成功"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除原料失败: {str(e)}")


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
