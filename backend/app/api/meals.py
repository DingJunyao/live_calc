"""
每日饮食推荐 API
"""
import datetime
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.api.deps import get_timezone
from app.utils.date_range_utils import utc_datetime_to_local_date
from app.models.user import User
from app.schemas.meal import MealRecommendationsResponse, RefreshMealRequest
from app.services.meal_recommender import (
    _build_response_from_records,
    check_today_status,
    is_refreshing,
    trigger_background_generation,
    trigger_background_refresh,
)

logger = logging.getLogger("meals")
router = APIRouter()


@router.get("/recommendations", response_model=MealRecommendationsResponse)
async def get_daily_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tz: str = Depends(get_timezone),
):
    """
    获取今日三餐推荐（轻量，不触发计算）。

    - 已有缓存 → 直接返回 status="ready"
    - 未生成 → 返回 status="not_generated"，前端应调用 POST /generate 触发后台计算
    - 生成中 → 返回 status="generating"，前端继续轮询

    耗时计算通过 POST /recommendations/generate 在后台线程中完成。
    """
    try:
        status_info = check_today_status(db, current_user.id, tz)

        if status_info["status"] == "ready":
            return await _build_response_from_records(
                db, status_info["existing_records"], current_user,
                refreshing_meals=status_info.get("refreshing_meals", []),
                tz=tz,
            )

        # not_generated 或 generating
        return MealRecommendationsResponse(
            status=status_info["status"],
            date=utc_datetime_to_local_date(datetime.datetime.now(datetime.timezone.utc), tz).isoformat(),
            recommendations=[],
            totals=None,
            refreshing_meals=status_info.get("refreshing_meals", []),
        )
    except Exception as e:
        logger.error(f"获取每日推荐失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取每日推荐失败",
        )


@router.post("/recommendations/generate", response_model=MealRecommendationsResponse)
async def trigger_recommendation_generation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tz: str = Depends(get_timezone),
):
    """
    触发后台生成今日推荐。

    - 已有缓存 → 直接返回（不重复生成）
    - 已在生成中 → 返回 status="generating"
    - 未生成 → 启动后台线程生成，返回 status="generating"
    """
    try:
        status_info = check_today_status(db, current_user.id, tz)

        if status_info["status"] == "ready":
            return await _build_response_from_records(
                db, status_info["existing_records"], current_user,
                refreshing_meals=status_info.get("refreshing_meals", []),
                tz=tz,
            )

        started = trigger_background_generation(current_user.id, tz)

        return MealRecommendationsResponse(
            status="generating",
            date=utc_datetime_to_local_date(datetime.datetime.now(datetime.timezone.utc), tz).isoformat(),
            recommendations=[],
            totals=None,
            refreshing_meals=[],
        )
    except Exception as e:
        logger.error(f"触发推荐生成失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="触发推荐生成失败",
        )


@router.post("/recommendations/refresh", response_model=MealRecommendationsResponse)
async def refresh_recommendation(
    request: RefreshMealRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tz: str = Depends(get_timezone),
):
    """
    刷新某一餐的推荐（后台异步模式）。

    - 触发后台线程重新打分选取最优菜谱
    - 立即返回当前推荐 + refreshing_meals 中含该餐标识
    - 前端应轮询 GET /recommendations 直到 refreshing_meals 不含该餐
    - 每餐每天最多刷新 5 次，超出返回 429
    - 该餐已在刷新中 → 返回 409
    """
    from app.services.meal_recommender import _count_today_refreshes

    try:
        # 先检查刷新次数
        today = utc_datetime_to_local_date(datetime.datetime.now(datetime.timezone.utc), tz)
        counts = _count_today_refreshes(db, current_user.id, today)
        current_count = counts.get(request.meal_type, 0)
        if current_count >= 5:
            raise HTTPException(
                status_code=429,
                detail=f"今天{request.meal_type}推荐已经刷新 5 次了，明天再来吧～",
            )

        # 检查是否已在刷新
        if is_refreshing(current_user.id, request.meal_type):
            # 返回当前推荐，frontend 可以继续轮询
            status_info = check_today_status(db, current_user.id, tz)
            if status_info["status"] == "ready":
                return await _build_response_from_records(
                    db, status_info["existing_records"], current_user,
                    refreshing_meals=status_info.get("refreshing_meals", []),
                )
            return MealRecommendationsResponse(
                status="generating",
                date=today.isoformat(),
                recommendations=[],
                totals=None,
                refreshing_meals=status_info.get("refreshing_meals", []),
            )

        # 确保推荐已存在（否则应该先走 generate）
        status_info = check_today_status(db, current_user.id, tz)
        if status_info["status"] != "ready":
            return MealRecommendationsResponse(
                status="not_generated",
                date=today.isoformat(),
                recommendations=[],
                totals=None,
            )

        # 触发后台刷新
        started, error = trigger_background_refresh(
            current_user.id, request.meal_type, tz
        )
        if not started:
            raise HTTPException(status_code=409, detail=error)

        # 返回当前推荐 + 刷新中标记
        return await _build_response_from_records(
            db, status_info["existing_records"], current_user,
            refreshing_meals=[request.meal_type],
            tz=tz,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"刷新推荐失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="刷新推荐失败",
        )
