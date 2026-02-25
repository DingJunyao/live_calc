from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.location import Location, FavoriteLocation
from app.schemas.location import (
    LocationCreate,
    LocationResponse,
    FavoriteLocationCreate,
    FavoriteLocationResponse,
    RouteCalculateRequest,
    RouteCalculateResponse
)
from app.services.map_service import calculate_route

router = APIRouter()


@router.post("/", response_model=LocationResponse)
async def create_location(
    location: LocationCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建地点"""
    try:
        db_location = Location(
            user_id=current_user.id,
            name=location.name,
            address=location.address,
            latitude=location.latitude,
            longitude=location.longitude
        )
        db.add(db_location)
        db.commit()
        db.refresh(db_location)
        return db_location
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建地点失败: {str(e)}")


@router.get("/", response_model=List[LocationResponse])
async def get_locations(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取地点列表"""
    try:
        locations = db.query(Location).filter(
            Location.user_id == current_user.id
        ).order_by(Location.created_at.desc()).all()
        return locations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取地点失败: {str(e)}")


@router.get("/favorites/", response_model=List[FavoriteLocationResponse])
async def get_favorite_locations(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取常用位置"""
    try:
        favorites = db.query(FavoriteLocation).filter(
            FavoriteLocation.user_id == current_user.id
        ).order_by(FavoriteLocation.created_at.desc()).all()
        return favorites
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取常用位置失败: {str(e)}")


@router.post("/favorites/", response_model=FavoriteLocationResponse)
async def create_favorite_location(
    location: FavoriteLocationCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建常用位置"""
    try:
        db_location = FavoriteLocation(
            user_id=current_user.id,
            name=location.name,
            type=location.type,
            latitude=location.latitude,
            longitude=location.longitude
        )
        db.add(db_location)
        db.commit()
        db.refresh(db_location)
        return db_location
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建常用位置失败: {str(e)}")


@router.post("/route", response_model=RouteCalculateResponse)
async def calculate_location_route(
    request: RouteCalculateRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """计算路线"""
    from_location = db.query(FavoriteLocation).filter(
        FavoriteLocation.id == request.from_location_id,
        FavoriteLocation.user_id == current_user.id
    ).first()
    if not from_location:
        raise HTTPException(status_code=404, detail="起点不存在")

    to_location = db.query(Location).filter(
        Location.id == request.to_location_id,
        Location.user_id == current_user.id
    ).first()
    if not to_location:
        raise HTTPException(status_code=404, detail="终点不存在")

    # 计算路线
    result = calculate_route(
        (float(from_location.latitude), float(from_location.longitude)),
        (float(to_location.latitude), float(to_location.longitude)),
        request.travel_mode,
        request.map_provider
    )

    return RouteCalculateResponse(**result)
