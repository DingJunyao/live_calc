"""
独立的迷你图数据 API

提供批量查询各类实体的近N天价格/成本趋势数据，
与主列表 API 分离，避免列表加载超时。
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from collections import defaultdict
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.product import ProductRecord
from app.models.product_entity import Product
from app.models.nutrition import Ingredient
from app.models.recipe import Recipe

router = APIRouter(tags=["sparklines"])


def _daily_avg_for_product_ids(
    db: Session,
    product_ids: List[int],
    days: int = 90,
) -> List[float]:
    """计算一组商品在近N天内的每日平均价格"""
    if not product_ids:
        return []

    cutoff = datetime.utcnow() - timedelta(days=days)
    records = db.query(
        ProductRecord.product_id,
        ProductRecord.price,
        ProductRecord.original_quantity,
        ProductRecord.recorded_at,
    ).filter(
        ProductRecord.product_id.in_(product_ids),
        ProductRecord.recorded_at >= cutoff,
        ProductRecord.price.isnot(None),
    ).order_by(ProductRecord.recorded_at).all()

    daily_totals: dict = defaultdict(lambda: {"sum": 0.0, "count": 0})
    for prod_id, price, qty, recorded_at in records:
        qty_f = float(qty) if qty and float(qty) > 0 else 1.0
        unit_price = float(price) / qty_f
        date_key = recorded_at.strftime("%Y-%m-%d")
        daily_totals[date_key]["sum"] += unit_price
        daily_totals[date_key]["count"] += 1

    return [
        round(daily_totals[d]["sum"] / daily_totals[d]["count"], 2)
        for d in sorted(daily_totals.keys())
    ]


@router.get("/sparklines/recipes")
async def get_recipes_sparklines(
    ids: str = Query(..., description="菜谱ID列表，逗号分隔"),
    days: int = Query(90, ge=7, le=365, description="查询天数"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, Optional[List[float]]]:
    """批量获取菜谱迷你图数据（多线程并发）"""
    try:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
        if not id_list:
            return {}

        from app.core.database import SessionLocal
        from app.services.recipe_service import calculate_recipe_cost_range_trend

        def _compute_one(rid: int) -> tuple:
            """在独立 DB session 中计算单个菜谱的成本趋势"""
            session = SessionLocal()
            try:
                trend = calculate_recipe_cost_range_trend(rid, current_user.id, session, days=days)
                if trend:
                    data = [t["avg_cost"] for t in trend if t.get("avg_cost") is not None]
                    return (str(rid), data if data else None)
                return (str(rid), None)
            except Exception:
                return (str(rid), None)
            finally:
                session.close()

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=min(len(id_list), 8)) as pool:
            futures = [loop.run_in_executor(pool, _compute_one, rid) for rid in id_list]
            results = await asyncio.gather(*futures)

        return {k: v for k, v in results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取菜谱迷你图失败: {str(e)}")


@router.get("/sparklines/ingredients")
async def get_ingredients_sparklines(
    ids: str = Query(..., description="原料ID列表，逗号分隔"),
    days: int = Query(90, ge=7, le=365, description="查询天数"),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
) -> Dict[str, Optional[List[float]]]:
    """批量获取原料迷你图数据（跨所有关联商品聚合）"""
    try:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
        if not id_list:
            return {}

        # 批量查询原料→商品映射
        products = db.query(Product.id, Product.ingredient_id).filter(
            Product.ingredient_id.in_(id_list),
            Product.is_active == True,
        ).all()

        ing_to_prods: dict = defaultdict(list)
        for prod_id, ing_id in products:
            ing_to_prods[ing_id].append(prod_id)

        # 对每个原料计算聚合 sparkline
        result: dict = {}
        for ing_id in id_list:
            prod_ids = ing_to_prods.get(ing_id, [])
            data = _daily_avg_for_product_ids(db, prod_ids, days=days)
            result[str(ing_id)] = data if data else None

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取原料迷你图失败: {str(e)}")


@router.get("/sparklines/products")
async def get_products_sparklines(
    ids: str = Query(..., description="商品ID列表，逗号分隔"),
    days: int = Query(90, ge=7, le=365, description="查询天数"),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
) -> Dict[str, Optional[List[float]]]:
    """批量获取商品迷你图数据"""
    try:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
        if not id_list:
            return {}

        result: dict = {}
        for pid in id_list:
            data = _daily_avg_for_product_ids(db, [pid], days=days)
            result[str(pid)] = data if data else None

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取商品迷你图失败: {str(e)}")
