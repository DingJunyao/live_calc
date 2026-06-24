"""
每日饮食推荐 API
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.meal import MealRecommendationsResponse, RefreshMealRequest
from app.services.meal_recommender import (
    generate_recommendations,
    refresh_meal_recommendation,
)

logger = logging.getLogger("meals")
router = APIRouter()


@router.get("/recommendations", response_model=MealRecommendationsResponse)
async def get_daily_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取今日三餐推荐。

    - 首次访问时执行推荐算法，写入 daily_recommendations 表
    - 再次访问时从表中读取缓存结果
    - is_current_meal 根据服务端当前时间判断（5-10→早餐, 10-14→午餐, 14-22→晚餐）
    """
    try:
        result = await generate_recommendations(db, current_user)
        return result
    except Exception as e:
        logger.error(f"获取每日推荐失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取每日推荐失败",
        )


@router.post("/recommendations/refresh", response_model=MealRecommendationsResponse)
async def refresh_recommendation(
    request: RefreshMealRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    刷新某一餐的推荐。

    - 排除当前推荐的菜谱，重新打分选取最优
    - 每餐每天最多刷新 5 次，超出返回 429
    """
    try:
        result, error = await refresh_meal_recommendation(
            db, current_user, request.meal_type
        )
        if error:
            if "次了" in error and "刷新" in error:
                raise HTTPException(status_code=429, detail=error)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"刷新推荐失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="刷新推荐失败",
        )
