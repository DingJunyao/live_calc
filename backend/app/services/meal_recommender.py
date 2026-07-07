"""
每日饮食推荐服务

核心推荐算法：按用户营养目标和预算，从候选菜谱池中打分排序，
为早/午/晚三餐各选最优菜谱。
"""
import asyncio
import datetime
import logging
import random
import threading
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text

from app.models.user import User
from app.models.recipe import Recipe
from app.models.daily_recommendation import DailyRecommendation
from app.services.recipe_service import calculate_recipe_cost, calculate_recipe_nutrition

logger = logging.getLogger("meal_recommender")

# 后台生成追踪：记录哪些用户正在生成推荐
_generating_users: Set[int] = set()
_generation_lock = threading.Lock()

# 后台刷新追踪：记录哪些用户正在刷新某一餐
_refreshing_meals: Dict[int, Set[str]] = {}
_refresh_lock = threading.Lock()

# 三餐营养占比
MEAL_RATIOS = {
    "breakfast": 0.25,
    "lunch": 0.40,
    "dinner": 0.35,
}

# 每餐每天最大刷新次数
MAX_REFRESH_PER_MEAL = 5


def _get_meal_targets(user: User, meal_type: str) -> Dict[str, float]:
    """根据用户目标和三餐占比计算某餐的期望值。"""
    ratio = MEAL_RATIOS[meal_type]
    return {
        "calories": (user.daily_calorie_target or 2000) * ratio,
        "protein": (user.daily_protein_target or 60) * ratio,
        "carbs": (user.daily_carb_target or 300) * ratio,
        "fat": (user.daily_fat_target or 65) * ratio,
    }


def _calc_nutrition_score(nutrition: Optional[Dict], targets: Dict[str, float]) -> float:
    """
    计算营养得分 [0, 1]。

    对热量/蛋白质/碳水/脂肪四项，每项计算：
      偏差 = 1 - |实际值 - 期望值| / max(期望值, 1)
    返回四项偏差的平均值。
    """
    if not nutrition:
        return 0.0

    per_serving = nutrition.get("per_serving", {})
    if not per_serving:
        return 0.0

    actual = {
        "calories": float(per_serving.get("calories", 0) or 0),
        "protein": float(per_serving.get("protein", 0) or 0),
        "carbs": float(per_serving.get("carbs", 0) or 0),
        "fat": float(per_serving.get("fat", 0) or 0),
    }

    deviations = []
    for key in ["calories", "protein", "carbs", "fat"]:
        target = targets[key]
        actual_val = actual[key]
        max_val = max(target, 1.0)
        dev = 1.0 - min(abs(actual_val - target) / max_val, 1.0)
        deviations.append(max(dev, 0.0))

    return sum(deviations) / len(deviations)


def _calc_cost_score(cost_data: Optional[Dict], user: User, meal_type: str) -> float:
    """
    计算成本得分 [0, 1]。

    cost_score = 1 - min(recipe_cost / meal_budget, 1)
    daily_budget 为 None 时返回 0.5（中性分）。
    """
    if user.daily_budget is None or user.daily_budget <= 0:
        return 0.5

    meal_budget = user.daily_budget * MEAL_RATIOS[meal_type]
    if meal_budget <= 0:
        return 0.0

    cost_per_serving = float((cost_data or {}).get("cost_per_serving", 0) or 0)
    if cost_per_serving <= 0:
        return 1.0

    return 1.0 - min(cost_per_serving / meal_budget, 1.0)


def _get_candidate_pool(
    db: Session, meal_type: str, exclude_recipe_ids: Optional[Set[int]] = None,
    user_id: Optional[int] = None
) -> List[Recipe]:
    """
    获取某餐类的候选菜谱池。

    规则：
    - breakfast: category == "早餐"
    - lunch/dinner: category != "早餐"（共享候选池）
    - is_active == True
    - 排除 exclude_recipe_ids 中的菜谱（用于午/晚餐去重）
    """
    query = db.query(Recipe).filter(Recipe.is_active == True)

    if meal_type == "breakfast":
        query = query.filter(Recipe.category == "早餐")
    else:
        query = query.filter(
            (Recipe.category != "早餐") | (Recipe.category == None) | (Recipe.category == "")
        )

    if exclude_recipe_ids:
        query = query.filter(~Recipe.id.in_(exclude_recipe_ids))

    # 排除用户黑名单中原料对应的菜谱（手动 + 分组订阅）
    if user_id is not None:
        from app.api.blacklist import _get_effective_blacklist_ids
        from app.models.recipe import RecipeIngredient

        blacklisted_ids = _get_effective_blacklist_ids(db, user_id)

        if blacklisted_ids:
            excluded_recipes = db.query(RecipeIngredient.recipe_id).filter(
                RecipeIngredient.ingredient_id.in_(blacklisted_ids),
            ).distinct().all()
            excluded_set = {r[0] for r in excluded_recipes}
            if excluded_set:
                query = query.filter(~Recipe.id.in_(excluded_set))

    return query.all()


async def _score_recipe(
    db: Session,
    user: User,
    recipe: Recipe,
    meal_type: str,
    targets: Dict[str, float],
) -> Tuple[float, Optional[Dict], Optional[Dict]]:
    """对单个菜谱打分，返回 (score, nutrition_data, cost_data)。"""
    nutrition = None
    cost = None

    try:
        nutrition = await calculate_recipe_nutrition(recipe.id, db=db)
    except Exception:
        logger.debug(f"菜谱 {recipe.id} ({recipe.name}) 营养计算失败", exc_info=True)

    try:
        cost = await calculate_recipe_cost(recipe.id, user.id, db=db)
    except Exception:
        logger.debug(f"菜谱 {recipe.id} ({recipe.name}) 成本计算失败", exc_info=True)

    if nutrition is None and cost is None:
        return (0.0, None, None)

    n_score = _calc_nutrition_score(nutrition, targets) if nutrition else 0.0
    c_score = _calc_cost_score(cost, user, meal_type) if cost else 0.5
    score = n_score * 0.5 + c_score * 0.5

    return (score, nutrition, cost)


async def _pick_best_recipe(
    user: User,
    meal_type: str,
    exclude_recipe_ids: Optional[Set[int]] = None,
    db: Optional[Session] = None,
) -> Tuple[Optional[Recipe], Optional[Dict], Optional[Dict], float]:
    """从候选池中按分数加权随机选取一道菜谱。"""
    candidates = _get_candidate_pool(db, meal_type, exclude_recipe_ids, user_id=user.id)
    # 释放候选池查询的读事务（SHARED 锁），避免 generate 后台长读事务阻塞并发写
    # （SQLite 写 commit 需 EXCLUSIVE 锁，被 SHARED 阻塞至 busy_timeout 超时）
    db.rollback()
    if not candidates:
        return (None, None, None, 0.0)

    targets = _get_meal_targets(user, meal_type)

    # 收集全部候选的打分（读 + 计算，不持写锁）
    scored: List[Tuple[Recipe, float, Optional[Dict], Optional[Dict]]] = []
    for recipe in candidates:
        score, nutrition, cost = await _score_recipe(db, user, recipe, meal_type, targets)
        # 每个候选打分后释放读事务（SHARED 锁），让并发写（如 POST /products）
        # 能在候选间隙拿到 EXCLUSIVE 锁，避免等至 busy_timeout 超时
        db.rollback()
        scored.append((recipe, score, nutrition, cost))

    if not scored:
        return (None, None, None, 0.0)

    # 加权随机：权重 = score + epsilon。
    # 直接用分数做权重（不放大幂次）——高分更易中、低分也有机会，
    # 让每天生成与每次「换一个」都能推出不同菜，避免确定性 argmax 导致天天老三样。
    # epsilon 保证 score=0（营养/成本都算不出）的菜也有微机会，且 weights 不全零。
    epsilon = 0.05
    weights = [s + epsilon for (_, s, _, _) in scored]
    best_recipe, best_score, best_nutrition, best_cost = random.choices(
        scored, weights=weights, k=1
    )[0]

    return (best_recipe, best_nutrition, best_cost, best_score)


def _build_recipe_brief(
    recipe: Recipe, nutrition: Optional[Dict], cost: Optional[Dict]
) -> Dict:
    """构建菜谱简要信息 dict。"""
    brief = {
        "id": recipe.id,
        "name": recipe.name,
        "category": recipe.category,
        "images": recipe.images or [],
        "servings": recipe.servings or 1,
    }

    if cost:
        brief["cost_estimate"] = round(float(cost.get("cost_per_serving", 0) or 0), 2)
    else:
        brief["cost_estimate"] = None

    if nutrition:
        per_serving = nutrition.get("per_serving", {})
        brief["nutrition_per_serving"] = {
            "calories": round(float(per_serving.get("calories", 0) or 0), 1),
            "protein_g": round(float(per_serving.get("protein", 0) or 0), 1),
            "carbs_g": round(float(per_serving.get("carbs", 0) or 0), 1),
            "fat_g": round(float(per_serving.get("fat", 0) or 0), 1),
        }
    else:
        brief["nutrition_per_serving"] = None

    return brief


def _count_today_refreshes(
    db: Session, user_id: int, today: datetime.date
) -> Dict[str, int]:
    """查询今天各餐已刷新次数（首次生成不算刷新）。"""
    result = db.execute(
        text(
            "SELECT meal_type, COUNT(*) as cnt FROM daily_recommendations "
            "WHERE user_id = :uid AND date = :date "
            "GROUP BY meal_type"
        ),
        {"uid": user_id, "date": today},
    ).fetchall()

    counts = {"breakfast": 0, "lunch": 0, "dinner": 0}
    for row in result:
        meal_type = row[0]
        counts[meal_type] = max(0, row[1] - 1)
    return counts


def _get_current_meal(hour: int) -> Optional[str]:
    """根据当前小时判断对应餐类。"""
    if 5 <= hour < 10:
        return "breakfast"
    elif 10 <= hour < 14:
        return "lunch"
    elif 14 <= hour < 22:
        return "dinner"
    return None


async def _build_response_from_records(
    db: Session, records: List[DailyRecommendation], user: User,
    refreshing_meals: Optional[List[str]] = None,
) -> Dict:
    """从 daily_recommendations 记录构建完整响应。"""
    now = datetime.datetime.now()
    current_meal = _get_current_meal(now.hour)
    today = datetime.date.today()

    refresh_counts = _count_today_refreshes(db, user.id, today)

    # 过滤掉包含黑名单原料的推荐（用户可能后来修改了黑名单）
    from app.api.blacklist import _get_effective_blacklist_ids
    from app.models.recipe import RecipeIngredient

    blacklisted_ids = _get_effective_blacklist_ids(db, user.id)
    blocked_recipe_ids: set[int] = set()
    if blacklisted_ids:
        record_recipe_ids = [r.recipe_id for r in records if r and r.recipe_id]
        if record_recipe_ids:
            blocked_recipe_ids = set(
                r[0] for r in db.query(RecipeIngredient.recipe_id).filter(
                    RecipeIngredient.recipe_id.in_(record_recipe_ids),
                    RecipeIngredient.ingredient_id.in_(blacklisted_ids),
                ).distinct().all()
            )
    # 有被黑名单屏蔽的推荐时，异步触发后台刷新相应餐类
    if blocked_recipe_ids:
        blocked_meal_types = {r.meal_type for r in records if r.recipe_id in blocked_recipe_ids}
        for mt in blocked_meal_types:
            trigger_background_refresh(user.id, mt)
        refreshing_meals = list(set((refreshing_meals or []) + list(blocked_meal_types)))

    rec_map = {r.meal_type: r for r in records}
    recommendations = []
    totals = {
        "cost": 0.0,
        "calories": 0.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 0.0,
    }

    for meal_type in ["breakfast", "lunch", "dinner"]:
        record = rec_map.get(meal_type)
        # 跳过被黑名单屏蔽的推荐
        if record and record.recipe and record.recipe_id in blocked_recipe_ids:
            recommendations.append({
                "meal_type": meal_type,
                "recipe": None,
                "is_current_meal": (meal_type == current_meal),
            })
            continue

        if record and record.recipe:
            recipe = record.recipe
            try:
                nutrition = await calculate_recipe_nutrition(recipe.id, db=db)
            except Exception:
                logger.debug(f"响应构建：菜谱 {recipe.id} 营养计算失败", exc_info=True)
                nutrition = None
            try:
                cost = await calculate_recipe_cost(recipe.id, user.id, db=db)
            except Exception:
                logger.debug(f"响应构建：菜谱 {recipe.id} 成本计算失败", exc_info=True)
                cost = None

            brief = _build_recipe_brief(recipe, nutrition, cost)
            recommendations.append(
                {
                    "meal_type": meal_type,
                    "recipe": brief,
                    "is_current_meal": (meal_type == current_meal),
                }
            )

            if cost:
                totals["cost"] = round(
                    totals["cost"] + float(cost.get("cost_per_serving", 0) or 0), 2
                )
            if nutrition:
                ps = nutrition.get("per_serving", {})
                totals["calories"] = round(
                    totals["calories"] + float(ps.get("calories", 0) or 0), 1
                )
                totals["protein_g"] = round(
                    totals["protein_g"] + float(ps.get("protein", 0) or 0), 1
                )
                totals["carbs_g"] = round(
                    totals["carbs_g"] + float(ps.get("carbs", 0) or 0), 1
                )
                totals["fat_g"] = round(
                    totals["fat_g"] + float(ps.get("fat", 0) or 0), 1
                )
        else:
            recommendations.append(
                {
                    "meal_type": meal_type,
                    "recipe": None,
                    "is_current_meal": (meal_type == current_meal),
                }
            )

    totals["refresh_counts"] = refresh_counts

    return {
        "status": "ready",
        "date": today.isoformat(),
        "recommendations": recommendations,
        "totals": totals,
        "refreshing_meals": refreshing_meals or [],
    }


async def generate_recommendations(db: Session, user: User) -> Dict:
    """
    为指定用户生成今日三餐推荐。

    逻辑：
    1. 检查今天是否已有推荐，有则直接读取返回
    2. 对每餐候选池打分排序，选最优
    3. 写入 daily_recommendations
    4. 返回结果
    """
    today = datetime.date.today()

    existing = (
        db.query(DailyRecommendation)
        .options(joinedload(DailyRecommendation.recipe))
        .filter(
            DailyRecommendation.user_id == user.id,
            DailyRecommendation.date == today,
        )
        .all()
    )

    if existing:
        # 检查已有推荐是否包含黑名单原料（用户可能后来修改了黑名单）
        from app.api.blacklist import _get_effective_blacklist_ids
        from app.models.recipe import RecipeIngredient

        blacklisted_ids = _get_effective_blacklist_ids(db, user.id)
        if blacklisted_ids:
            existing_recipe_ids = [r.recipe_id for r in existing if r.recipe_id]
            if existing_recipe_ids:
                bl_recipe_ids = set(
                    r[0] for r in db.query(RecipeIngredient.recipe_id).filter(
                        RecipeIngredient.recipe_id.in_(existing_recipe_ids),
                        RecipeIngredient.ingredient_id.in_(blacklisted_ids),
                    ).distinct().all()
                )
                if bl_recipe_ids:
                    # 删除包含黑名单原料的推荐记录
                    bl_meal_types = {r.meal_type for r in existing if r.recipe_id in bl_recipe_ids}
                    db.query(DailyRecommendation).filter(
                        DailyRecommendation.user_id == user.id,
                        DailyRecommendation.date == today,
                        DailyRecommendation.meal_type.in_(bl_meal_types),
                    ).delete(synchronize_session=False)
                    db.commit()
                    # 保留未被黑名单影响的推荐
                    existing = [r for r in existing if r.recipe_id not in bl_recipe_ids]

                    # 为被删除的餐重新生成推荐（先算后写，避免长事务持锁阻塞并发写）
                    picked_ids = {r.recipe_id for r in existing if r.recipe_id}
                    regen_picks: list = []
                    for mt in ["breakfast", "lunch", "dinner"]:
                        if mt not in bl_meal_types:
                            continue
                        best, nutrition, cost, score = await _pick_best_recipe(
                            user, mt, exclude_recipe_ids=picked_ids, db=db,
                        )
                        if best:
                            picked_ids.add(best.id)
                            regen_picks.append((mt, best.id))
                    for mt, rid in regen_picks:
                        db.add(DailyRecommendation(
                            user_id=user.id, date=today, meal_type=mt, recipe_id=rid,
                        ))
                    db.commit()
                    # 重新读取完整记录
                    existing = (
                        db.query(DailyRecommendation)
                        .options(joinedload(DailyRecommendation.recipe))
                        .filter(
                            DailyRecommendation.user_id == user.id,
                            DailyRecommendation.date == today,
                        )
                        .all()
                    )

        if existing:
            return await _build_response_from_records(db, existing, user)

    meal_types = ["breakfast", "lunch", "dinner"]
    picked_ids: Set[int] = set()  # 午/晚餐共享候选池，防止重复

    # 先完成所有餐的打分挑选（读 + 计算，不持写锁），再批量写入 + commit。
    # 避免循环内 add+flush 后继续 _pick_best_recipe（计算密集）导致写锁持有整个循环，
    # 阻塞并发写（如 POST /products 等 SQLite 写锁至 busy_timeout 30s 超时）。
    picks: list = []
    for meal_type in meal_types:
        best_recipe, nutrition, cost, score = await _pick_best_recipe(
            user, meal_type, exclude_recipe_ids=picked_ids, db=db
        )
        if best_recipe:
            picked_ids.add(best_recipe.id)
            picks.append((meal_type, best_recipe.id))

    # 批量写入 + commit（写锁持有时间短）
    for meal_type, recipe_id in picks:
        db.add(DailyRecommendation(
            user_id=user.id, date=today, meal_type=meal_type, recipe_id=recipe_id,
        ))
    db.commit()

    all_records = (
        db.query(DailyRecommendation)
        .options(joinedload(DailyRecommendation.recipe))
        .filter(
            DailyRecommendation.user_id == user.id,
            DailyRecommendation.date == today,
        )
        .all()
    )

    return await _build_response_from_records(db, all_records, user)


async def refresh_meal_recommendation(
    db: Session, user: User, meal_type: str
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    刷新某一餐的推荐。

    返回 (response_dict, error_message)。
    成功时 error_message 为 None；失败时 response_dict 为 None。
    """
    today = datetime.date.today()

    refresh_counts = _count_today_refreshes(db, user.id, today)
    current_count = refresh_counts.get(meal_type, 0)
    if current_count >= MAX_REFRESH_PER_MEAL:
        return (
            None,
            f"今天{meal_type}推荐已经刷新 {MAX_REFRESH_PER_MEAL} 次了，明天再来吧～",
        )

    current_rec = (
        db.query(DailyRecommendation)
        .filter(
            DailyRecommendation.user_id == user.id,
            DailyRecommendation.date == today,
            DailyRecommendation.meal_type == meal_type,
        )
        .first()
    )

    # 收集其他餐已选菜谱，确保刷新后不会与其他餐重复
    exclude_ids: Set[int] = set()
    all_today = (
        db.query(DailyRecommendation)
        .filter(
            DailyRecommendation.user_id == user.id,
            DailyRecommendation.date == today,
            DailyRecommendation.meal_type != meal_type,
        )
        .all()
    )
    for rec in all_today:
        exclude_ids.add(rec.recipe_id)

    # 也排除当前餐已有的菜谱（如果存在），避免刷到同一个
    if current_rec:
        exclude_ids.add(current_rec.recipe_id)

    best_recipe, nutrition, cost, score = await _pick_best_recipe(
        user, meal_type, exclude_recipe_ids=exclude_ids, db=db
    )

    if not best_recipe:
        return (None, "该餐类暂无其他可用菜谱")

    if current_rec:
        # 直接更新已有记录的 recipe_id，避免 delete+insert 的事务问题
        current_rec.recipe_id = best_recipe.id
    else:
        # 当天首次刷新该餐（理论上不会走到这里，但做兜底）
        new_rec = DailyRecommendation(
            user_id=user.id,
            date=today,
            meal_type=meal_type,
            recipe_id=best_recipe.id,
        )
        db.add(new_rec)

    db.commit()

    # commit 后重新查询，eager-load recipe 避免懒加载问题
    all_records = (
        db.query(DailyRecommendation)
        .options(joinedload(DailyRecommendation.recipe))
        .filter(
            DailyRecommendation.user_id == user.id,
            DailyRecommendation.date == today,
        )
        .all()
    )

    return (await _build_response_from_records(db, all_records, user), None)


# ============ 后台生成与状态检查 ============

def is_generating(user_id: int) -> bool:
    """检查指定用户是否正在后台生成推荐。"""
    with _generation_lock:
        return user_id in _generating_users


def check_today_status(db: Session, user_id: int) -> Dict:
    """快速检查今日推荐状态，不触发耗时计算。

    返回 {"status": ..., "existing_records": [...], "refreshing_meals": [...]}，
    status 为 "ready"（已有）+ records、"not_generated"（无）、"generating"（生成中）。
    refreshing_meals 为当前正在后台刷新的餐类列表（仅在 ready 时有意义）。
    """
    today = datetime.date.today()

    existing = (
        db.query(DailyRecommendation)
        .options(joinedload(DailyRecommendation.recipe))
        .filter(
            DailyRecommendation.user_id == user_id,
            DailyRecommendation.date == today,
        )
        .all()
    )

    with _refresh_lock:
        refreshing = list(_refreshing_meals.get(user_id, set()))

    if existing:
        return {"status": "ready", "existing_records": existing, "refreshing_meals": refreshing}
    if is_generating(user_id):
        return {"status": "generating", "existing_records": [], "refreshing_meals": refreshing}
    return {"status": "not_generated", "existing_records": [], "refreshing_meals": refreshing}


def _generate_in_background(user_id: int):
    """在独立线程中运行推荐生成，不阻塞 HTTP 响应。"""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            logger.warning(f"后台生成：用户 {user_id} 不存在")
            return
        # 在新线程中跑独立的 event loop
        asyncio.run(generate_recommendations(db, user))
        logger.info(f"后台生成：用户 {user_id} 推荐已就绪")
    except Exception:
        logger.exception(f"后台生成：用户 {user_id} 推荐失败")
    finally:
        db.close()
        with _generation_lock:
            _generating_users.discard(user_id)


def trigger_background_generation(user_id: int) -> bool:
    """触发后台生成。如果已在生成中返回 False，否则启动线程并返回 True。"""
    with _generation_lock:
        if user_id in _generating_users:
            return False
        _generating_users.add(user_id)

    thread = threading.Thread(
        target=_generate_in_background,
        args=(user_id,),
        daemon=True,
        name=f"meal-gen-{user_id}",
    )
    thread.start()
    return True


# ============ 后台刷新 ============

def is_refreshing(user_id: int, meal_type: str) -> bool:
    """检查指定用户的某餐是否正在后台刷新。"""
    with _refresh_lock:
        return meal_type in _refreshing_meals.get(user_id, set())


def _refresh_in_background(user_id: int, meal_type: str):
    """在独立线程中运行单餐刷新。"""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            logger.warning(f"后台刷新：用户 {user_id} 不存在")
            return
        result, error = asyncio.run(refresh_meal_recommendation(db, user, meal_type))
        if error:
            logger.warning(f"后台刷新：用户 {user_id} {meal_type} 刷新失败: {error}")
        else:
            logger.info(f"后台刷新：用户 {user_id} {meal_type} 已更新")
    except Exception:
        logger.exception(f"后台刷新：用户 {user_id} {meal_type} 异常")
    finally:
        db.close()
        with _refresh_lock:
            meals = _refreshing_meals.get(user_id, set())
            meals.discard(meal_type)
            if not meals:
                _refreshing_meals.pop(user_id, None)


def trigger_background_refresh(user_id: int, meal_type: str) -> Tuple[bool, Optional[str]]:
    """触发后台刷新某餐。返回 (started, error_message)。

    - 已在刷新中 → (False, "该餐正在刷新中")
    - 启动成功 → (True, None)
    """
    with _refresh_lock:
        meals = _refreshing_meals.setdefault(user_id, set())
        if meal_type in meals:
            return (False, "该餐正在刷新中，请稍候～")
        meals.add(meal_type)

    thread = threading.Thread(
        target=_refresh_in_background,
        args=(user_id, meal_type),
        daemon=True,
        name=f"meal-refresh-{user_id}-{meal_type}",
    )
    thread.start()
    return (True, None)
