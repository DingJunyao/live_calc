"""用户原料黑名单 API（支持手动添加 + 原料黑名单分组订阅）"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Set
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.user_ingredient_blacklist import UserIngredientBlacklist
from app.models.blacklist_group_subscription import BlacklistGroupSubscription
from app.models.blacklist_group import BlacklistGroup, BlacklistGroupIngredient
from app.models.nutrition import Ingredient
from app.schemas.blacklist import (
    BlacklistCreate, BlacklistBatchCreate, BlacklistBatchDelete,
    BlacklistResponse, BlacklistIngredientIdsResponse,
    BlacklistGroupSubscribe, BlacklistGroupResponse,
)

router = APIRouter(tags=["blacklist"])


def _get_effective_blacklist_ids(db: Session, user_id: int) -> Set[int]:
    """计算用户的有效黑名单原料 ID 集合：手动 + 所有已订阅分组的原料"""
    ids: Set[int] = set()

    # 手动添加的（只计 source='manual'，旧版 source='blacklist_group' 的复制条目不再生效）
    manual = db.query(UserIngredientBlacklist.ingredient_id).filter(
        UserIngredientBlacklist.user_id == user_id,
        UserIngredientBlacklist.source == "manual",
        UserIngredientBlacklist.is_active == True,
    ).all()
    ids.update(r[0] for r in manual)

    # 已订阅分组的原料（只计仍启用 is_active=True 的分组，与其他端点逻辑一致）
    subscribed_groups = db.query(BlacklistGroupSubscription.blacklist_group_id).filter(
        BlacklistGroupSubscription.user_id == user_id,
        BlacklistGroupSubscription.is_active == True,
    ).all()
    if subscribed_groups:
        group_ids = [r[0] for r in subscribed_groups]
        active_group_ids = [r[0] for r in db.query(BlacklistGroup.id).filter(
            BlacklistGroup.id.in_(group_ids),
            BlacklistGroup.is_active == True,
        ).all()]
        if active_group_ids:
            group_ingredients = db.query(BlacklistGroupIngredient.ingredient_id).filter(
                BlacklistGroupIngredient.group_id.in_(active_group_ids),
                BlacklistGroupIngredient.is_active == True,
            ).all()
            ids.update(r[0] for r in group_ingredients)

    return ids


def _build_response(entry: UserIngredientBlacklist) -> BlacklistResponse:
    ingredient_name = None
    if entry.ingredient:
        ingredient_name = entry.ingredient.name
    return BlacklistResponse(
        id=entry.id,
        user_id=entry.user_id,
        ingredient_id=entry.ingredient_id,
        ingredient_name=ingredient_name,
        reason=entry.reason,
        source=entry.source,
        blacklist_group_id=None,
        blacklist_group_name=None,
        created_at=entry.created_at,
        is_active=entry.is_active,
    )


# ---- 手动原料黑名单 CRUD ----

@router.get("/blacklist", response_model=List[BlacklistResponse])
@router.get("/blacklist/", response_model=List[BlacklistResponse])
def list_blacklist(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None, description="搜索原料名"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的手动黑名单列表"""
    query = db.query(UserIngredientBlacklist).filter(
        UserIngredientBlacklist.user_id == current_user.id,
        UserIngredientBlacklist.is_active == True,
        UserIngredientBlacklist.source == "manual",
    )
    if search:
        query = query.join(Ingredient, UserIngredientBlacklist.ingredient_id == Ingredient.id).filter(
            Ingredient.name.ilike(f"%{search}%")
        )
    entries = query.order_by(UserIngredientBlacklist.created_at.desc()).offset(skip).limit(limit).all()
    return [_build_response(e) for e in entries]


@router.post("/blacklist", response_model=BlacklistResponse)
@router.post("/blacklist/", response_model=BlacklistResponse)
def add_to_blacklist(
    body: BlacklistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """添加单个原料到黑名单"""
    existing = db.query(UserIngredientBlacklist).filter(
        UserIngredientBlacklist.user_id == current_user.id,
        UserIngredientBlacklist.ingredient_id == body.ingredient_id,
    ).first()
    if existing:
        if existing.is_active and existing.source == "manual":
            return _build_response(existing)
        existing.is_active = True
        existing.reason = body.reason
        existing.source = "manual"
        existing.blacklist_group_id = None
        existing.updated_by = current_user.id
        db.commit()
        db.refresh(existing)
        return _build_response(existing)

    entry = UserIngredientBlacklist(
        user_id=current_user.id,
        ingredient_id=body.ingredient_id,
        reason=body.reason,
        source="manual",
        created_by=current_user.id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _build_response(entry)


@router.delete("/blacklist/{ingredient_id}")
@router.delete("/blacklist/{ingredient_id}/")
def remove_from_blacklist(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """移除单个手动添加的原料（软删除）"""
    entry = db.query(UserIngredientBlacklist).filter(
        UserIngredientBlacklist.user_id == current_user.id,
        UserIngredientBlacklist.ingredient_id == ingredient_id,
        UserIngredientBlacklist.source == "manual",
        UserIngredientBlacklist.is_active == True,
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="该原料不在黑名单中")
    entry.is_active = False
    entry.updated_by = current_user.id
    db.commit()
    return {"message": "已移除"}


# ---- 原料黑名单分组订阅 ----

@router.get("/blacklist/groups", response_model=List[BlacklistGroupResponse])
@router.get("/blacklist/groups/", response_model=List[BlacklistGroupResponse])
def list_subscribed_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户已订阅的原料黑名单分组及当前原料列表"""
    subs = db.query(BlacklistGroupSubscription).filter(
        BlacklistGroupSubscription.user_id == current_user.id,
        BlacklistGroupSubscription.is_active == True,
    ).all()
    result = []
    for sub in subs:
        group = db.query(BlacklistGroup).filter(BlacklistGroup.id == sub.blacklist_group_id).first()
        if not group or not group.is_active:
            continue
        ingredients = db.query(BlacklistGroupIngredient).filter(
            BlacklistGroupIngredient.group_id == group.id,
            BlacklistGroupIngredient.is_active == True,
        ).all()
        ingredient_list = []
        for agi in ingredients:
            if agi.ingredient and agi.ingredient.is_active:
                ingredient_list.append({"id": agi.ingredient_id, "name": agi.ingredient.name})
        result.append(BlacklistGroupResponse(
            id=group.id,
            name=group.name,
            ingredient_count=len(ingredient_list),
            ingredients=ingredient_list,
        ))
    return result


@router.post("/blacklist/groups")
@router.post("/blacklist/groups/")
def subscribe_groups(
    body: BlacklistGroupSubscribe,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """订阅原料黑名单分组（已订阅的跳过）"""
    added = 0
    for gid in body.group_ids:
        existing = db.query(BlacklistGroupSubscription).filter(
            BlacklistGroupSubscription.user_id == current_user.id,
            BlacklistGroupSubscription.blacklist_group_id == gid,
        ).first()
        if existing:
            if not existing.is_active:
                existing.is_active = True
                existing.updated_by = current_user.id
                added += 1
        else:
            sub = BlacklistGroupSubscription(
                user_id=current_user.id,
                blacklist_group_id=gid,
                created_by=current_user.id,
            )
            db.add(sub)
            added += 1
    db.commit()
    return {"message": f"已订阅 {added} 个分组", "count": added}


@router.delete("/blacklist/groups/{group_id}")
@router.delete("/blacklist/groups/{group_id}/")
def unsubscribe_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """取消订阅原料黑名单分组"""
    sub = db.query(BlacklistGroupSubscription).filter(
        BlacklistGroupSubscription.user_id == current_user.id,
        BlacklistGroupSubscription.blacklist_group_id == group_id,
        BlacklistGroupSubscription.is_active == True,
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="未订阅该分组")
    sub.is_active = False
    sub.updated_by = current_user.id
    db.commit()
    return {"message": "已取消订阅"}


# ---- 有效黑名单（手动 + 分组订阅的并集） ----

@router.get("/blacklist/ingredient-ids", response_model=BlacklistIngredientIdsResponse)
@router.get("/blacklist/ingredient-ids/", response_model=BlacklistIngredientIdsResponse)
def get_blacklist_ingredient_ids(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户有效黑名单中所有 ingredient_id（手动 + 已订阅分组的并集）"""
    ids = _get_effective_blacklist_ids(db, current_user.id)
    return BlacklistIngredientIdsResponse(ingredient_ids=sorted(ids))
