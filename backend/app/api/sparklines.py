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
    ingredient_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> List[float]:
    """计算一组商品在近N天内的每日平均价格。

    - 传 ingredient_id：商品内日均 → 商品间按 price_weight 加权（原料 sparkline 用，
      修正「记录多的商品被放大」的偏置）。
    - 不传：退化为记录级日均（旧行为，商品 sparkline 用）。
    归一化到 ¥/斤（1斤=500g），按 standard_quantity 确保跨单位可比。
    """
    if not product_ids:
        return []

    cutoff = datetime.utcnow() - timedelta(days=days)
    records = db.query(
        ProductRecord.product_id,
        ProductRecord.price,
        ProductRecord.standard_quantity,
        ProductRecord.recorded_at,
    ).filter(
        ProductRecord.product_id.in_(product_ids),
        ProductRecord.recorded_at >= cutoff,
        ProductRecord.price.isnot(None),
    ).order_by(ProductRecord.recorded_at).all()

    # 权重表：全局 price_weight
    pw: dict = {pid: w for pid, w in db.query(Product.id, Product.price_weight)
                .filter(Product.id.in_(product_ids)).all()}
    # 用户覆盖（优先于全局）
    if user_id is not None:
        from app.models.user_product_weight_override import UserProductWeightOverride
        ov = {r.product_id: r.weight for r in db.query(UserProductWeightOverride).filter(
            UserProductWeightOverride.user_id == user_id,
            UserProductWeightOverride.product_id.in_(product_ids),
            UserProductWeightOverride.is_active == True,  # noqa: E712
        ).all()}
        pw = {k: ov.get(k, v) for k, v in pw.items()}

    # 按日 + 按商品：{date: {product_id: [unit_price,...]}}
    by_day_product: dict = defaultdict(dict)
    for prod_id, price, std_qty, recorded_at in records:
        std_qty_f = float(std_qty) if std_qty and float(std_qty) > 0 else 500.0
        unit_price = float(price) * 500.0 / std_qty_f
        dkey = recorded_at.strftime("%Y-%m-%d")
        by_day_product[dkey].setdefault(prod_id, []).append(unit_price)

    result: List[float] = []
    for dkey in sorted(by_day_product.keys()):
        prods = by_day_product[dkey]
        if ingredient_id is not None:
            # 商品级加权：每商品先均价，再按权重加权
            num = den = 0.0
            for pid, ups in prods.items():
                w = pw.get(pid, 50)
                if w <= 0 or not ups:
                    continue
                num += (sum(ups) / len(ups)) * w
                den += w
            avg = num / den if den > 0 else None
        else:
            all_up = [up for ups in prods.values() for up in ups]
            avg = sum(all_up) / len(all_up) if all_up else None
        if avg is not None:
            result.append(round(avg, 2))
    return result


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
            data = _daily_avg_for_product_ids(db, prod_ids, days=days, ingredient_id=ing_id, user_id=_current_user.id)
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
