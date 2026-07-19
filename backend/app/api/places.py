from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user_place import UserPlace
from app.models.map_config import MapConfiguration
from app.schemas.user_place import (
    UserPlaceCreate,
    UserPlaceUpdate,
    UserPlaceResponse,
)

router = APIRouter()


def _ensure_map_enabled(db: Session) -> None:
    """地图功能关闭时拒绝写操作（读接口不拦，数据保留）。"""
    config = db.query(MapConfiguration).first()
    enabled = bool(config.map_enabled) if config else True
    if not enabled:
        raise HTTPException(status_code=403, detail="地图功能已关闭，无法维护常用地点")


def _clear_default(db: Session, user_id: int) -> None:
    """把该用户的其他地点 is_default 置 False（保证全局唯一默认）。"""
    db.query(UserPlace).filter(
        UserPlace.user_id == user_id,
        UserPlace.is_default == True,  # noqa: E712
    ).update({UserPlace.is_default: False})


@router.get("", response_model=List[UserPlaceResponse])
async def list_user_places(
    db: Session = Depends(get_db),
    current_user= Depends(get_current_user),
):
    """获取当前用户的常用地点列表（is_default 优先，其次 sort_order、created_at）。"""
    try:
        return (
            db.query(UserPlace)
            .filter(UserPlace.user_id == current_user.id)
            .order_by(
                UserPlace.is_default.desc(),
                UserPlace.sort_order.asc(),
                UserPlace.created_at.asc(),
            )
            .all()
        )
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="获取常用地点失败")


@router.post("", response_model=UserPlaceResponse, status_code=201)
async def create_user_place(
    place: UserPlaceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """新建常用地点。若 is_default=True，联动清除该用户其他默认。"""
    try:
        _ensure_map_enabled(db)
        if place.is_default:
            _clear_default(db, current_user.id)
        db_place = UserPlace(
            user_id=current_user.id,
            name=place.name,
            kind=place.kind,
            latitude=place.latitude,
            longitude=place.longitude,
            address=place.address,
            is_default=bool(place.is_default),
            sort_order=place.sort_order or 0,
        )
        db.add(db_place)
        db.commit()
        db.refresh(db_place)
        return db_place
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="创建常用地点失败")


@router.put("/{place_id}", response_model=UserPlaceResponse)
async def update_user_place(
    place_id: int,
    place: UserPlaceUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """更新常用地点（改名/坐标/类型等）。"""
    try:
        _ensure_map_enabled(db)
        db_place = db.query(UserPlace).filter(
            UserPlace.id == place_id,
            UserPlace.user_id == current_user.id,
        ).first()
        if not db_place:
            raise HTTPException(status_code=404, detail="常用地点不存在")
        for k, v in place.model_dump(exclude_unset=True).items():
            setattr(db_place, k, v)
        db.commit()
        db.refresh(db_place)
        return db_place
    except HTTPException:
        raise
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="更新常用地点失败")


@router.delete("/{place_id}")
async def delete_user_place(
    place_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """删除常用地点。"""
    try:
        _ensure_map_enabled(db)
        db_place = db.query(UserPlace).filter(
            UserPlace.id == place_id,
            UserPlace.user_id == current_user.id,
        ).first()
        if not db_place:
            raise HTTPException(status_code=404, detail="常用地点不存在")
        db.delete(db_place)
        db.commit()
        return {"message": "常用地点已删除"}
    except HTTPException:
        raise
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="删除常用地点失败")


@router.put("/{place_id}/default", response_model=UserPlaceResponse)
async def set_default_user_place(
    place_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """将指定地点设为默认（联动清除该用户其他默认）。"""
    try:
        _ensure_map_enabled(db)
        db_place = db.query(UserPlace).filter(
            UserPlace.id == place_id,
            UserPlace.user_id == current_user.id,
        ).first()
        if not db_place:
            raise HTTPException(status_code=404, detail="常用地点不存在")
        _clear_default(db, current_user.id)
        db_place.is_default = True
        db.commit()
        db.refresh(db_place)
        return db_place
    except HTTPException:
        raise
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="设置默认地点失败")
