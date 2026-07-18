"""原料黑名单分组 API（管理员维护 + 公开只读）"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user
from app.models.user import User
from app.models.blacklist_group import BlacklistGroup, BlacklistGroupIngredient
from app.models.blacklist_group_subscription import BlacklistGroupSubscription
from app.models.user_ingredient_blacklist import UserIngredientBlacklist
from app.models.nutrition import Ingredient
from app.schemas.blacklist_group import (
    BlacklistGroupCreate, BlacklistGroupUpdate,
    BlacklistGroupResponse, BlacklistGroupIngredientResponse,
    BlacklistGroupPublicResponse, BlacklistGroupIngredientCreate,
)

blacklist_group_admin_router = APIRouter(tags=["原料黑名单分组管理"])
blacklist_group_public_router = APIRouter(tags=["原料黑名单分组"])


def _build_ingredient_response(agi: BlacklistGroupIngredient) -> BlacklistGroupIngredientResponse:
    name = agi.ingredient.name if agi.ingredient else None
    return BlacklistGroupIngredientResponse(
        id=agi.id,
        ingredient_id=agi.ingredient_id,
        ingredient_name=name,
        is_ai_matched=agi.is_ai_matched,
    )


def _build_group_response(group: BlacklistGroup) -> BlacklistGroupResponse:
    # 只统计 is_active 的原料映射（单个原料删除是软删除）
    ingredients = [i for i in (group.group_ingredients or []) if i.is_active]
    return BlacklistGroupResponse(
        id=group.id,
        name=group.name,
        display_order=group.display_order or 0,
        is_active=group.is_active if group.is_active is not None else True,
        ingredients=[_build_ingredient_response(i) for i in ingredients],
        ingredient_count=len(ingredients),
        created_at=group.created_at,
    )


# ---- 管理员端点 ----

@blacklist_group_admin_router.get("/blacklist-groups", response_model=List[BlacklistGroupResponse])
@blacklist_group_admin_router.get("/blacklist-groups/", response_model=List[BlacklistGroupResponse])
def list_groups(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """管理员：获取原料黑名单分组列表（只显示未删除的）"""
    groups = db.query(BlacklistGroup).filter(
        BlacklistGroup.is_active == True
    ).options(
        joinedload(BlacklistGroup.group_ingredients).joinedload(BlacklistGroupIngredient.ingredient)
    ).order_by(BlacklistGroup.display_order, BlacklistGroup.id).all()
    return [_build_group_response(g) for g in groups]


@blacklist_group_admin_router.post("/blacklist-groups", response_model=BlacklistGroupResponse)
@blacklist_group_admin_router.post("/blacklist-groups/", response_model=BlacklistGroupResponse)
def create_group(
    body: BlacklistGroupCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """创建原料黑名单分组"""
    existing = db.query(BlacklistGroup).filter(BlacklistGroup.name == body.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="分组名已存在")
    group = BlacklistGroup(
        name=body.name,
        display_order=body.display_order,
        created_by=admin.id,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    group.group_ingredients = []
    return _build_group_response(group)


@blacklist_group_admin_router.put("/blacklist-groups/{group_id}", response_model=BlacklistGroupResponse)
@blacklist_group_admin_router.put("/blacklist-groups/{group_id}/", response_model=BlacklistGroupResponse)
def update_group(
    group_id: int,
    body: BlacklistGroupUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """编辑原料黑名单分组"""
    group = db.query(BlacklistGroup).options(
        joinedload(BlacklistGroup.group_ingredients).joinedload(BlacklistGroupIngredient.ingredient)
    ).filter(BlacklistGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(group, field, value)
    group.updated_by = admin.id
    db.commit()
    db.refresh(group)
    return _build_group_response(group)


@blacklist_group_admin_router.delete("/blacklist-groups/{group_id}")
@blacklist_group_admin_router.delete("/blacklist-groups/{group_id}/")
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """删除原料黑名单分组（软删除：仅置 is_active=False，原料映射和用户订阅保留以便恢复）

    用户端三个端点都过滤 group.is_active=True，故软删除后自动对用户失效；
    恢复（is_active=True）后自动重新生效。
    """
    group = db.query(BlacklistGroup).filter(BlacklistGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")
    group.is_active = False
    group.updated_by = admin.id
    db.commit()
    return {"message": "已删除"}


@blacklist_group_admin_router.post("/blacklist-groups/{group_id}/ingredients", response_model=BlacklistGroupResponse)
@blacklist_group_admin_router.post("/blacklist-groups/{group_id}/ingredients/", response_model=BlacklistGroupResponse)
def add_ingredients_to_group(
    group_id: int,
    body: BlacklistGroupIngredientCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """添加原料到分组"""
    group = db.query(BlacklistGroup).options(
        joinedload(BlacklistGroup.group_ingredients).joinedload(BlacklistGroupIngredient.ingredient)
    ).filter(BlacklistGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")
    for ing_id in body.ingredient_ids:
        existing = db.query(BlacklistGroupIngredient).filter(
            BlacklistGroupIngredient.group_id == group_id,
            BlacklistGroupIngredient.ingredient_id == ing_id,
        ).first()
        if existing:
            if not existing.is_active:
                existing.is_active = True
                existing.updated_by = admin.id
        else:
            agi = BlacklistGroupIngredient(
                group_id=group_id,
                ingredient_id=ing_id,
                created_by=admin.id,
            )
            db.add(agi)
    db.commit()
    db.refresh(group)
    return _build_group_response(group)


@blacklist_group_admin_router.delete("/blacklist-groups/{group_id}/ingredients/{ingredient_id}")
@blacklist_group_admin_router.delete("/blacklist-groups/{group_id}/ingredients/{ingredient_id}/")
def remove_ingredient_from_group(
    group_id: int,
    ingredient_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """从分组中移除原料"""
    agi = db.query(BlacklistGroupIngredient).filter(
        BlacklistGroupIngredient.group_id == group_id,
        BlacklistGroupIngredient.ingredient_id == ingredient_id,
        BlacklistGroupIngredient.is_active == True,
    ).first()
    if not agi:
        raise HTTPException(status_code=404, detail="该原料不在分组中")
    agi.is_active = False
    agi.updated_by = admin.id
    db.commit()
    return {"message": "已移除"}


class AiMatchResponse(BaseModel):
    agent_session_id: int
    message: str


@blacklist_group_admin_router.post("/blacklist-groups/{group_id}/ai-match", response_model=AiMatchResponse)
@blacklist_group_admin_router.post("/blacklist-groups/{group_id}/ai-match/", response_model=AiMatchResponse)
def trigger_ai_match(
    group_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """触发 AI Agent 匹配原料黑名单分组原料"""
    group = db.query(BlacklistGroup).filter(BlacklistGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")

    from app.services.agent.blacklist_group_task import trigger_blacklist_group_match

    main_loop = asyncio.get_running_loop()
    session_id = trigger_blacklist_group_match(db, group_id, group.name, admin.id, main_loop)

    return AiMatchResponse(
        agent_session_id=session_id,
        message="已触发 AI 匹配任务，可在 Agent 任务台查看进度",
    )


@blacklist_group_admin_router.get("/blacklist-groups/allergens-status")
@blacklist_group_admin_router.get("/blacklist-groups/allergens-status/")
def get_allergens_status(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """管理员：获取过敏原分组导入状态（决定「快速导入」按钮显隐）"""
    from app.services.allergen_seed import need_allergen_seed
    return need_allergen_seed(db)


@blacklist_group_admin_router.post("/blacklist-groups/seed-allergens")
@blacklist_group_admin_router.post("/blacklist-groups/seed-allergens/")
def seed_allergens(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """管理员：一键导入/补全 GB 7718-2025 的 13 类过敏原分组（upsert 幂等）"""
    from app.services.allergen_seed import upsert_allergen_groups
    result = upsert_allergen_groups(db)
    return {
        "message": (
            f"导入完成：新建 {result['created']} 个分组，"
            f"复活 {result['reactivated']} 个分组，映射 {result['mapped']} 条原料"
        ),
        "stats": result,
    }


# ---- 公开只读端点 ----

@blacklist_group_public_router.get("/blacklist-groups", response_model=List[BlacklistGroupPublicResponse])
@blacklist_group_public_router.get("/blacklist-groups/", response_model=List[BlacklistGroupPublicResponse])
def get_public_groups(
    db: Session = Depends(get_db),
):
    """获取启用的原料黑名单分组（用户端快速选择用，无需登录）"""
    groups = db.query(BlacklistGroup).filter(BlacklistGroup.is_active == True).options(
        joinedload(BlacklistGroup.group_ingredients).joinedload(BlacklistGroupIngredient.ingredient)
    ).order_by(BlacklistGroup.display_order, BlacklistGroup.id).all()
    result = []
    for g in groups:
        active_ingredients = [
            agi for agi in (g.group_ingredients or [])
            if agi.is_active and agi.ingredient and agi.ingredient.is_active
        ]
        result.append(BlacklistGroupPublicResponse(
            id=g.id,
            name=g.name,
            ingredient_ids=[agi.ingredient_id for agi in active_ingredients],
            ingredient_names=[agi.ingredient.name for agi in active_ingredients if agi.ingredient],
        ))
    return result
