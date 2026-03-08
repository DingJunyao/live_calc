from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.merchant import Merchant, FavoriteMerchant
from app.schemas.merchant import (
    MerchantCreate,
    MerchantResponse,
    FavoriteMerchantCreate,
    FavoriteMerchantResponse,
    RouteCalculateRequest,
    RouteCalculateResponse
)
from app.schemas.common import PaginatedResponse
from app.services.map_service import calculate_route

router = APIRouter()


@router.post("", response_model=MerchantResponse)
async def create_merchant(
    merchant: MerchantCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建商家"""
    try:
        db_merchant = Merchant(
            user_id=current_user.id,
            name=merchant.name,
            address=merchant.address,
            latitude=merchant.latitude,
            longitude=merchant.longitude
        )
        db.add(db_merchant)
        db.commit()
        db.refresh(db_merchant)
        return db_merchant
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="创建商家时发生错误，请稍后重试"
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="创建商家时发生未知错误"
        )


@router.get("", response_model=PaginatedResponse[MerchantResponse])
async def get_merchants(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(10, ge=1, le=100, description="每页记录数"),
    search: Optional[str] = Query(None, description="搜索关键词（商家名称或地址）"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取商家列表（支持分页和搜索）"""
    try:
        # 构建查询
        query = db.query(Merchant).filter(
            Merchant.user_id == current_user.id
        )

        # 添加搜索条件
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Merchant.name.like(search_pattern),
                    Merchant.address.like(search_pattern)
                )
            )

        # 获取总数
        total = query.count()

        # 分页查询
        merchants = query.order_by(Merchant.created_at.desc()).offset(skip).limit(limit).all()

        # 计算页码
        page = (skip // limit) + 1

        # 返回分页响应
        return PaginatedResponse.create(
            items=merchants,
            total=total,
            page=page,
            page_size=limit
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="获取商家列表时发生错误，请稍后重试"
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="获取商家列表时发生未知错误"
        )


@router.get("/favorites", response_model=List[FavoriteMerchantResponse])
async def get_favorite_merchants(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取常用商家"""
    try:
        favorites = db.query(FavoriteMerchant).filter(
            FavoriteMerchant.user_id == current_user.id
        ).order_by(FavoriteMerchant.created_at.desc()).all()
        return favorites
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="获取常用商家时发生错误，请稍后重试"
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="获取常用商家时发生未知错误"
        )


@router.post("/favorites", response_model=FavoriteMerchantResponse)
async def create_favorite_merchant(
    merchant: FavoriteMerchantCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建常用商家"""
    try:
        db_merchant = FavoriteMerchant(
            user_id=current_user.id,
            name=merchant.name,
            type=merchant.type,
            latitude=merchant.latitude,
            longitude=merchant.longitude
        )
        db.add(db_merchant)
        db.commit()
        db.refresh(db_merchant)
        return db_merchant
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="创建常用商家时发生错误，请稍后重试"
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="创建常用商家时发生未知错误"
        )


@router.post("/route", response_model=RouteCalculateResponse)
async def calculate_merchant_route(
    request: RouteCalculateRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """计算路线"""
    from_merchant = db.query(FavoriteMerchant).filter(
        FavoriteMerchant.id == request.from_location_id,
        FavoriteMerchant.user_id == current_user.id
    ).first()
    if not from_merchant:
        raise HTTPException(status_code=404, detail="起点商家不存在")

    to_merchant = db.query(Merchant).filter(
        Merchant.id == request.to_location_id,
        Merchant.user_id == current_user.id
    ).first()
    if not to_merchant:
        raise HTTPException(status_code=404, detail="终点商家不存在")

    try:
        # 计算路线
        result = calculate_route(
            (float(from_merchant.latitude), float(from_merchant.longitude)),
            (float(to_merchant.latitude), float(to_merchant.longitude)),
            request.travel_mode,
            request.map_provider
        )

        return RouteCalculateResponse(**result)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="无效的坐标数据"
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="计算路线时发生错误，请稍后重试"
        )
