from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.unit_conversion_service import UnitConversionService
from app.services.ingredient_matcher import IngredientMatcher
from app.models.ingredient_category import IngredientCategory
from app.models.unit import Unit
from app.models.nutrition import Ingredient

router = APIRouter()


@router.get("/units", response_model=List[dict])
async def get_units(
    unit_type: Optional[str] = Query(None, description="单位类型，如mass, volume, length"),
    is_common: Optional[bool] = Query(None, description="是否为常用单位"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取单位列表"""
    try:
        query = db.query(Unit).filter(Unit.is_active == True)

        if unit_type:
            query = query.filter(Unit.unit_type == unit_type)
        if is_common is not None:
            query = query.filter(Unit.is_common == is_common)

        units = query.all()

        return [{
            "id": unit.id,
            "name": unit.name,
            "abbreviation": unit.abbreviation,
            "plural_form": unit.plural_form,
            "unit_type": unit.unit_type,
            "si_factor": unit.si_factor,
            "is_si_base": unit.is_si_base,
            "is_common": unit.is_common,
            "display_order": unit.display_order
        } for unit in units]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取单位列表失败: {str(e)}")


@router.get("/unit-conversion/{value}/{from_unit}/{to_unit}", response_model=Optional[float])
async def convert_units(
    value: float,
    from_unit: str,
    to_unit: str,
    ingredient_name: Optional[str] = Query(None, description="食材名称，用于体积重量转换"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """单位转换"""
    try:
        service = UnitConversionService(db)

        if ingredient_name:
            if from_unit.lower() in ['ml', 'l', 'cup', 'tbsp', 'tsp'] and to_unit.lower() in ['g', 'kg', 'lb', 'oz', 'jin']:
                result = service.convert_volume_to_weight(value, from_unit, ingredient_name)
                if result:
                    converted_value, _ = result
                    final_result = service.convert(converted_value, "g", to_unit)
                    return final_result
            elif from_unit.lower() in ['g', 'kg', 'lb', 'oz', 'jin'] and to_unit.lower() in ['ml', 'l', 'cup', 'tbsp', 'tsp']:
                result = service.convert_weight_to_volume(value, from_unit, ingredient_name)
                if result:
                    converted_value, _ = result
                    final_result = service.convert(converted_value, "ml", to_unit)
                    return final_result

        result = service.convert(value, from_unit, to_unit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"单位转换失败: {str(e)}")


@router.get("/search-by-name/{name}", response_model=List[dict])
async def search_ingredients_by_name(
    name: str,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """按名称搜索食材"""
    try:
        matcher = IngredientMatcher(db)
        matches = matcher.match_product_to_ingredient(name)[:limit]

        results = []
        for ingredient, confidence in matches:
            if ingredient.is_active:
                results.append({
                    "id": ingredient.id,
                    "name": ingredient.name,
                    "category_id": ingredient.category_id,
                    "density": ingredient.density,
                    "default_unit": ingredient.default_unit,
                    "aliases": ingredient.aliases or [],
                    "confidence": float(confidence)
                })

        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索食材失败: {str(e)}")


@router.get("/hierarchy/{ingredient_id}", response_model=dict)
async def get_ingredient_hierarchy(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取食材的层级关系"""
    try:
        from app.models.ingredient_hierarchy import IngredientHierarchy

        ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id, Ingredient.is_active == True).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="食材不存在")

        parent_relations = db.query(IngredientHierarchy).filter(
            IngredientHierarchy.child_id == ingredient_id
        ).all()

        parents = []
        for rel in parent_relations:
            parent_ing = db.query(Ingredient).filter(Ingredient.id == rel.parent_id, Ingredient.is_active == True).first()
            if parent_ing:
                parents.append({
                    "id": parent_ing.id,
                    "name": parent_ing.name,
                    "relationship_type": rel.relationship_type,
                    "confidence": float(rel.confidence) if rel.confidence else 1.0
                })

        child_relations = db.query(IngredientHierarchy).filter(
            IngredientHierarchy.parent_id == ingredient_id
        ).all()

        children = []
        for rel in child_relations:
            child_ing = db.query(Ingredient).filter(Ingredient.id == rel.child_id, Ingredient.is_active == True).first()
            if child_ing:
                children.append({
                    "id": child_ing.id,
                    "name": child_ing.name,
                    "relationship_type": rel.relationship_type,
                    "confidence": float(rel.confidence) if rel.confidence else 1.0
                })

        return {
            "ingredient": {
                "id": ingredient.id,
                "name": ingredient.name,
                "category_id": ingredient.category_id,
                "density": ingredient.density,
                "default_unit": ingredient.default_unit,
                "aliases": ingredient.aliases or []
            },
            "parents": parents,
            "children": children
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取层级关系失败: {str(e)}")


@router.get("/categories", response_model=List[dict])
async def get_ingredient_categories(
    parent_id: Optional[int] = Query(None, description="父类别ID，为None时返回顶级类别"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取食材分类列表"""
    try:
        query = db.query(IngredientCategory).filter(IngredientCategory.is_active == True)

        if parent_id is not None:
            query = query.filter(IngredientCategory.parent_category_id == parent_id)
        else:
            query = query.filter(IngredientCategory.parent_category_id.is_(None))

        categories = query.all()

        return [{
            "id": cat.id,
            "name": cat.name,
            "display_name": cat.display_name,
            "parent_category_id": cat.parent_category_id,
            "sort_order": cat.sort_order,
            "description": cat.description
        } for cat in categories]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分类列表失败: {str(e)}")


@router.post("/resolve-hierarchy", response_model=Optional[dict])
async def resolve_ingredient_hierarchy(
    base_ingredient: str = Query(..., description="基础食材名称"),
    grade_requirement: Optional[str] = Query(None, description="等级要求，如高筋、中筋等"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """解析食材层级关系"""
    try:
        matcher = IngredientMatcher(db)
        ingredient = matcher.resolve_ingredient_hierarchy(base_ingredient, grade_requirement)

        if ingredient:
            return {
                "id": ingredient.id,
                "name": ingredient.name,
                "category_id": ingredient.category_id,
                "density": ingredient.density,
                "default_unit": ingredient.default_unit,
                "aliases": ingredient.aliases or []
            }
        else:
            return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析层级关系失败: {str(e)}")


@router.get("/alternatives/{ingredient_id}", response_model=List[dict])
async def get_ingredient_alternatives(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取食材替代选项"""
    try:
        ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id, Ingredient.is_active == True).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="食材不存在")

        matcher = IngredientMatcher(db)
        alternatives = matcher.suggest_alternatives(ingredient)

        return [{
            "id": alt.id,
            "name": alt.name,
            "category_id": alt.category_id,
            "density": alt.density,
            "default_unit": alt.default_unit,
            "aliases": alt.aliases or []
        } for alt in alternatives]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取替代选项失败: {str(e)}")


@router.post("", response_model=dict)
async def create_ingredient(
    name: str = Body(..., min_length=1),
    category_id: Optional[int] = Body(None),
    aliases: Optional[List[str]] = Body(None),
    density: Optional[float] = Body(None),
    default_unit: Optional[str] = Body(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建食材"""
    try:
        existing = db.query(Ingredient).filter(Ingredient.name == name).first()
        if existing:
            raise HTTPException(status_code=400, detail="食材已存在")

        new_ingredient = Ingredient(
            name=name,
            category_id=category_id,
            aliases=aliases or [],
            density=density,
            default_unit=default_unit,
            created_by=current_user.id
        )
        db.add(new_ingredient)
        db.commit()
        db.refresh(new_ingredient)

        return {
            "id": new_ingredient.id,
            "name": new_ingredient.name,
            "category_id": new_ingredient.category_id,
            "density": new_ingredient.density,
            "default_unit": new_ingredient.default_unit,
            "aliases": new_ingredient.aliases or [],
            "created_at": new_ingredient.created_at
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建食材失败: {str(e)}")


@router.put("/{ingredient_id}", response_model=dict)
async def update_ingredient(
    ingredient_id: int,
    name: Optional[str] = Body(None),
    category_id: Optional[int] = Body(None),
    aliases: Optional[List[str]] = Body(None),
    density: Optional[float] = Body(None),
    default_unit: Optional[str] = Body(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """更新食材"""
    try:
        ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="食材不存在")

        if name and name != ingredient.name:
            existing = db.query(Ingredient).filter(Ingredient.name == name).first()
            if existing:
                raise HTTPException(status_code=400, detail="食材已存在")
            ingredient.name = name

        if category_id is not None:
            ingredient.category_id = category_id
        if aliases is not None:
            ingredient.aliases = aliases
        if density is not None:
            ingredient.density = density
        if default_unit is not None:
            ingredient.default_unit = default_unit

        ingredient.updated_by = current_user.id

        db.commit()
        db.refresh(ingredient)

        return {
            "id": ingredient.id,
            "name": ingredient.name,
            "category_id": ingredient.category_id,
            "density": ingredient.density,
            "default_unit": ingredient.default_unit,
            "aliases": ingredient.aliases or [],
            "created_at": ingredient.created_at
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新食材失败: {str(e)}")


@router.delete("/{ingredient_id}/hard")
async def hard_delete_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """硬删除食材 - 永久删除"""
    try:
        ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="食材不存在")

        db.delete(ingredient)
        db.commit()

        return {"message": "食材已永久删除"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"硬删除食材失败: {str(e)}")


@router.get("", response_model=List[dict])
async def get_ingredients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: str = Query(None, alias="q"),
    category_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取食材列表"""
    try:
        query = db.query(Ingredient).filter(Ingredient.is_active == True)

        if search:
            # 搜索名称或别名
            query = query.filter(
                (Ingredient.name.contains(search)) |
                (Ingredient.aliases.contains(f'"{search}"'))  # JSON 数组搜索
            )

        if category_id:
            query = query.filter(Ingredient.category_id == category_id)

        ingredients = query.offset(skip).limit(limit).all()

        return [{
            "id": ing.id,
            "name": ing.name,
            "category_id": ing.category_id,
            "density": ing.density,
            "default_unit": ing.default_unit,
            "aliases": ing.aliases or [],
            "created_at": ing.created_at
        } for ing in ingredients]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取食材列表失败: {str(e)}")


@router.get("/{ingredient_id}", response_model=dict)
async def get_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取食材详情"""
    try:
        ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id, Ingredient.is_active == True).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="食材不存在")

        return {
            "id": ingredient.id,
            "name": ingredient.name,
            "category_id": ingredient.category_id,
            "density": ingredient.density,
            "default_unit": ingredient.default_unit,
            "aliases": ingredient.aliases or [],
            "created_at": ingredient.created_at
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取食材详情失败: {str(e)}")


@router.delete("/{ingredient_id}")
async def soft_delete_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """软删除食材 - 将is_active设置为False"""
    try:
        ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id, Ingredient.is_active == True).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="食材不存在")

        ingredient.is_active = False
        ingredient.updated_by = current_user.id
        db.commit()

        return {"message": "食材已软删除"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"软删除食材失败: {str(e)}")