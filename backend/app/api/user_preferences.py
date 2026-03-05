"""用户偏好 API 路由"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.user_ingredient_preference import UserIngredientPreference
from app.schemas.user_preference import UserPreferenceCreate, UserPreferenceUpdate, UserPreferenceResponse

router = APIRouter(tags=["preferences"])


@router.post("/preferences", response_model=UserPreferenceResponse)
@router.post("/preferences/", response_model=UserPreferenceResponse)
def set_preference(
    preference: UserPreferenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """设置用户食材偏好"""
    # 检查是否已存在
    existing = db.query(UserIngredientPreference).filter(
        UserIngredientPreference.user_id == current_user.id,
        UserIngredientPreference.ingredient_id == preference.ingredient_id
    ).first()

    if existing:
        # 更新现有偏好
        for field, value in preference.model_dump().items():
            setattr(existing, field, value)
        existing.updated_by = current_user.id
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # 创建新偏好
        db_preference = UserIngredientPreference(
            **preference.model_dump(),
            user_id=current_user.id,
            created_by=current_user.id
        )
        db.add(db_preference)
        db.commit()
        db.refresh(db_preference)
        return db_preference


@router.get("/preferences", response_model=List[UserPreferenceResponse])
@router.get("/preferences/", response_model=List[UserPreferenceResponse])
def list_preferences(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户偏好列表"""
    preferences = db.query(UserIngredientPreference).filter(
        UserIngredientPreference.user_id == current_user.id,
        UserIngredientPreference.is_active == True
    ).offset(skip).limit(limit).all()
    return preferences


@router.get("/preferences/{ingredient_id}", response_model=UserPreferenceResponse)
@router.get("/preferences/{ingredient_id}/", response_model=UserPreferenceResponse)
def get_preference(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户对特定食材的偏好"""
    preference = db.query(UserIngredientPreference).filter(
        UserIngredientPreference.user_id == current_user.id,
        UserIngredientPreference.ingredient_id == ingredient_id,
        UserIngredientPreference.is_active == True
    ).first()

    if not preference:
        raise HTTPException(status_code=404, detail="Preference not found")

    return preference


@router.put("/preferences/{ingredient_id}", response_model=UserPreferenceResponse)
@router.put("/preferences/{ingredient_id}/", response_model=UserPreferenceResponse)
def update_preference(
    ingredient_id: int,
    preference_update: UserPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新用户偏好"""
    preference = db.query(UserIngredientPreference).filter(
        UserIngredientPreference.user_id == current_user.id,
        UserIngredientPreference.ingredient_id == ingredient_id
    ).first()

    if not preference:
        raise HTTPException(status_code=404, detail="Preference not found")

    update_data = preference_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(preference, field, value)

    preference.updated_by = current_user.id
    db.commit()
    db.refresh(preference)
    return preference


@router.delete("/preferences/{ingredient_id}")
@router.delete("/preferences/{ingredient_id}/")
def delete_preference(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除用户偏好"""
    preference = db.query(UserIngredientPreference).filter(
        UserIngredientPreference.user_id == current_user.id,
        UserIngredientPreference.ingredient_id == ingredient_id
    ).first()

    if not preference:
        raise HTTPException(status_code=404, detail="Preference not found")

    preference.is_active = False
    preference.updated_by = current_user.id
    db.commit()
    return {"message": "Preference deleted successfully"}
