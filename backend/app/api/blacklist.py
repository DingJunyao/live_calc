"""用户原料黑名单 API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.user_ingredient_blacklist import UserIngredientBlacklist
from app.models.nutrition import Ingredient
from app.schemas.blacklist import (
    BlacklistCreate, BlacklistBatchCreate, BlacklistBatchDelete,
    BlacklistResponse, BlacklistIngredientIdsResponse,
)

router = APIRouter(tags=["blacklist"])


def _build_response(entry: UserIngredientBlacklist) -> BlacklistResponse:
    ingredient_name = None
    allergen_group_name = None
    if entry.ingredient:
        ingredient_name = entry.ingredient.name
    if entry.allergen_group:
        allergen_group_name = entry.allergen_group.name
    return BlacklistResponse(
        id=entry.id,
        user_id=entry.user_id,
        ingredient_id=entry.ingredient_id,
        ingredient_name=ingredient_name,
        reason=entry.reason,
        source=entry.source,
        allergen_group_id=entry.allergen_group_id,
        allergen_group_name=allergen_group_name,
        created_at=entry.created_at,
        is_active=entry.is_active,
    )


@router.get("/blacklist", response_model=List[BlacklistResponse])
@router.get("/blacklist/", response_model=List[BlacklistResponse])
def list_blacklist(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None, description="搜索原料名"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的黑名单列表"""
    query = db.query(UserIngredientBlacklist).filter(
        UserIngredientBlacklist.user_id == current_user.id,
        UserIngredientBlacklist.is_active == True,
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
        if existing.is_active:
            return _build_response(existing)
        existing.is_active = True
        existing.reason = body.reason
        existing.source = "manual"
        existing.allergen_group_id = None
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
    """移除单个原料（软删除）"""
    entry = db.query(UserIngredientBlacklist).filter(
        UserIngredientBlacklist.user_id == current_user.id,
        UserIngredientBlacklist.ingredient_id == ingredient_id,
        UserIngredientBlacklist.is_active == True,
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="该原料不在黑名单中")
    entry.is_active = False
    entry.updated_by = current_user.id
    db.commit()
    return {"message": "已移除"}


@router.post("/blacklist/batch", response_model=List[BlacklistResponse])
@router.post("/blacklist/batch/", response_model=List[BlacklistResponse])
def batch_add_blacklist(
    body: BlacklistBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量添加原料到黑名单（用于过敏原分组一键添加）"""
    results = []
    for ing_id in body.ingredient_ids:
        existing = db.query(UserIngredientBlacklist).filter(
            UserIngredientBlacklist.user_id == current_user.id,
            UserIngredientBlacklist.ingredient_id == ing_id,
        ).first()
        if existing:
            if existing.is_active:
                results.append(existing)
                continue
            existing.is_active = True
            existing.reason = body.reason
            existing.source = "allergen_group"
            existing.allergen_group_id = body.allergen_group_id
            existing.updated_by = current_user.id
            results.append(existing)
        else:
            entry = UserIngredientBlacklist(
                user_id=current_user.id,
                ingredient_id=ing_id,
                reason=body.reason,
                source="allergen_group",
                allergen_group_id=body.allergen_group_id,
                created_by=current_user.id,
            )
            db.add(entry)
            results.append(entry)
    db.commit()
    for r in results:
        db.refresh(r)
    return [_build_response(r) for r in results]


@router.delete("/blacklist/batch")
@router.delete("/blacklist/batch/")
def batch_remove_blacklist(
    body: BlacklistBatchDelete,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量移除原料（软删除）"""
    db.query(UserIngredientBlacklist).filter(
        UserIngredientBlacklist.user_id == current_user.id,
        UserIngredientBlacklist.ingredient_id.in_(body.ingredient_ids),
        UserIngredientBlacklist.is_active == True,
    ).update(
        {"is_active": False, "updated_by": current_user.id}, synchronize_session=False
    )
    db.commit()
    return {"message": f"已移除 {len(body.ingredient_ids)} 个原料"}


@router.get("/blacklist/ingredient-ids", response_model=BlacklistIngredientIdsResponse)
@router.get("/blacklist/ingredient-ids/", response_model=BlacklistIngredientIdsResponse)
def get_blacklist_ingredient_ids(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户黑名单中所有 ingredient_id（轻量接口）"""
    entries = db.query(UserIngredientBlacklist.ingredient_id).filter(
        UserIngredientBlacklist.user_id == current_user.id,
        UserIngredientBlacklist.is_active == True,
    ).all()
    return BlacklistIngredientIdsResponse(ingredient_ids=[e[0] for e in entries])
