"""过敏原分组 API（管理员维护 + 公开只读）"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user
from app.models.user import User
from app.models.allergen_group import AllergenGroup, AllergenGroupIngredient
from app.models.nutrition import Ingredient
from app.schemas.allergen_group import (
    AllergenGroupCreate, AllergenGroupUpdate,
    AllergenGroupResponse, AllergenGroupIngredientResponse,
    AllergenGroupPublicResponse, AllergenGroupIngredientCreate,
)

admin_router = APIRouter(tags=["过敏原分组管理"])
public_router = APIRouter(tags=["过敏原分组"])


def _build_ingredient_response(agi: AllergenGroupIngredient) -> AllergenGroupIngredientResponse:
    name = agi.ingredient.name if agi.ingredient else None
    return AllergenGroupIngredientResponse(
        id=agi.id,
        ingredient_id=agi.ingredient_id,
        ingredient_name=name,
        is_ai_matched=agi.is_ai_matched,
    )


def _build_group_response(group: AllergenGroup) -> AllergenGroupResponse:
    ingredients = group.group_ingredients or []
    return AllergenGroupResponse(
        id=group.id,
        name=group.name,
        display_order=group.display_order or 0,
        is_active=group.is_active if group.is_active is not None else True,
        ingredients=[_build_ingredient_response(i) for i in ingredients],
        ingredient_count=len(ingredients),
        created_at=group.created_at,
    )


# ---- 管理员端点 ----

@admin_router.get("/allergen-groups", response_model=List[AllergenGroupResponse])
@admin_router.get("/allergen-groups/", response_model=List[AllergenGroupResponse])
def list_groups(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """管理员：获取所有过敏原分组列表"""
    groups = db.query(AllergenGroup).options(
        joinedload(AllergenGroup.group_ingredients).joinedload(AllergenGroupIngredient.ingredient)
    ).order_by(AllergenGroup.display_order, AllergenGroup.id).all()
    return [_build_group_response(g) for g in groups]


@admin_router.post("/allergen-groups", response_model=AllergenGroupResponse)
@admin_router.post("/allergen-groups/", response_model=AllergenGroupResponse)
def create_group(
    body: AllergenGroupCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """创建过敏原分组"""
    existing = db.query(AllergenGroup).filter(AllergenGroup.name == body.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="分组名已存在")
    group = AllergenGroup(
        name=body.name,
        display_order=body.display_order,
        created_by=admin.id,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    group.group_ingredients = []
    return _build_group_response(group)


@admin_router.put("/allergen-groups/{group_id}", response_model=AllergenGroupResponse)
@admin_router.put("/allergen-groups/{group_id}/", response_model=AllergenGroupResponse)
def update_group(
    group_id: int,
    body: AllergenGroupUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """编辑过敏原分组"""
    group = db.query(AllergenGroup).options(
        joinedload(AllergenGroup.group_ingredients).joinedload(AllergenGroupIngredient.ingredient)
    ).filter(AllergenGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(group, field, value)
    group.updated_by = admin.id
    db.commit()
    db.refresh(group)
    return _build_group_response(group)


@admin_router.delete("/allergen-groups/{group_id}")
@admin_router.delete("/allergen-groups/{group_id}/")
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """删除过敏原分组（软删除）"""
    group = db.query(AllergenGroup).filter(AllergenGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")
    group.is_active = False
    group.updated_by = admin.id
    # 同时软删除关联的原料映射
    db.query(AllergenGroupIngredient).filter(
        AllergenGroupIngredient.group_id == group_id
    ).update({"is_active": False}, synchronize_session=False)
    db.commit()
    return {"message": "已删除"}


@admin_router.post("/allergen-groups/{group_id}/ingredients", response_model=AllergenGroupResponse)
@admin_router.post("/allergen-groups/{group_id}/ingredients/", response_model=AllergenGroupResponse)
def add_ingredients_to_group(
    group_id: int,
    body: AllergenGroupIngredientCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """添加原料到分组"""
    group = db.query(AllergenGroup).options(
        joinedload(AllergenGroup.group_ingredients).joinedload(AllergenGroupIngredient.ingredient)
    ).filter(AllergenGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")
    for ing_id in body.ingredient_ids:
        existing = db.query(AllergenGroupIngredient).filter(
            AllergenGroupIngredient.group_id == group_id,
            AllergenGroupIngredient.ingredient_id == ing_id,
        ).first()
        if existing:
            if not existing.is_active:
                existing.is_active = True
                existing.updated_by = admin.id
        else:
            agi = AllergenGroupIngredient(
                group_id=group_id,
                ingredient_id=ing_id,
                created_by=admin.id,
            )
            db.add(agi)
    db.commit()
    db.refresh(group)
    return _build_group_response(group)


@admin_router.delete("/allergen-groups/{group_id}/ingredients/{ingredient_id}")
@admin_router.delete("/allergen-groups/{group_id}/ingredients/{ingredient_id}/")
def remove_ingredient_from_group(
    group_id: int,
    ingredient_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """从分组中移除原料"""
    agi = db.query(AllergenGroupIngredient).filter(
        AllergenGroupIngredient.group_id == group_id,
        AllergenGroupIngredient.ingredient_id == ingredient_id,
        AllergenGroupIngredient.is_active == True,
    ).first()
    if not agi:
        raise HTTPException(status_code=404, detail="该原料不在分组中")
    agi.is_active = False
    agi.updated_by = admin.id
    db.commit()
    return {"message": "已移除"}


# ---- 公开只读端点 ----

@public_router.get("/allergen-groups", response_model=List[AllergenGroupPublicResponse])
@public_router.get("/allergen-groups/", response_model=List[AllergenGroupPublicResponse])
def get_public_groups(
    db: Session = Depends(get_db),
):
    """获取启用的过敏原分组（用户端快速选择用，无需登录）"""
    groups = db.query(AllergenGroup).filter(AllergenGroup.is_active == True).options(
        joinedload(AllergenGroup.group_ingredients).joinedload(AllergenGroupIngredient.ingredient)
    ).order_by(AllergenGroup.display_order, AllergenGroup.id).all()
    result = []
    for g in groups:
        active_ingredients = [
            agi for agi in (g.group_ingredients or [])
            if agi.is_active and agi.ingredient and agi.ingredient.is_active
        ]
        result.append(AllergenGroupPublicResponse(
            id=g.id,
            name=g.name,
            ingredient_ids=[agi.ingredient_id for agi in active_ingredients],
            ingredient_names=[agi.ingredient.name for agi in active_ingredients if agi.ingredient],
        ))
    return result
