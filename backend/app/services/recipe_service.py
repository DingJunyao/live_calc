from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Tuple
import json
from datetime import datetime, timedelta
from collections import defaultdict
from app.models.recipe import Recipe, RecipeIngredient
from app.models.product import ProductRecord
from app.models.product_entity import Product
from app.models.nutrition import Ingredient
from app.models.nutrition_data import NutritionData  # NutritionData 从 nutrition_data 导入，避免冲突
from app.models.ingredient_hierarchy import IngredientHierarchy, HierarchyRelationType
from decimal import Decimal


def _get_price_record_with_fallback(
    db: Session,
    user_id: int,
    product_id: int = None,
    as_of_date: datetime = None,
    product_name_contains: str = None
) -> Optional[ProductRecord]:
    """
    获取价格记录，带前向填充（Forward Fill）机制

    首先尝试查找指定日期之前的最新记录，如果找不到，则使用该食材/商品
    在整个时间段中的最早记录。这样可以避免因价格记录维护不及时导致的
    成本陡增现象。

    Args:
        db: 数据库会话
        user_id: 用户ID
        product_id: 商品ID（可选，与 product_name_contains 二选一）
        as_of_date: 指定日期（可选，如果不指定则返回最新记录）
        product_name_contains: 商品名称包含的字符串（可选，用于名称匹配）

    Returns:
        ProductRecord: 价格记录，如果找不到则返回 None
    """
    # 构建基础查询条件
    query = db.query(ProductRecord).filter(
        ProductRecord.user_id == user_id
    )

    if product_id:
        query = query.filter(ProductRecord.product_id == product_id)

    if product_name_contains:
        query = query.filter(ProductRecord.product_name.contains(product_name_contains))

    # 如果指定了日期，首先尝试查找该日期之前的最新记录
    if as_of_date:
        query_with_date = query.filter(ProductRecord.recorded_at <= as_of_date)
        latest_record = query_with_date.order_by(ProductRecord.recorded_at.desc()).first()

        if latest_record:
            # 找到了指定日期之前的记录，直接返回
            return latest_record

    # 如果没找到指定日期之前的记录，或者没有指定日期，则查找最早的记录
    # 这实现了前向填充（Forward Fill）机制
    earliest_record = query.order_by(ProductRecord.recorded_at.asc()).first()

    return earliest_record


def _get_price_records_for_date(
    db: Session,
    user_id: int,
    ingredient_id: int,
    as_of_date: datetime,
    product_id: int = None
) -> List[ProductRecord]:
    """
    获取某食材在指定日期的所有价格记录

    Args:
        db: 数据库会话
        user_id: 用户ID
        ingredient_id: 食材ID
        as_of_date: 指定日期
        product_id: 可选，指定商品ID，不指定则查找该食材下的第一个商品

    Returns:
        当天的所有价格记录列表
    """
    # 计算当天的开始和结束时间
    day_start = as_of_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1) - timedelta(microseconds=1)

    if product_id is not None:
        # 使用指定的商品ID查询
        product = db.query(Product).filter(
            Product.id == product_id,
            Product.is_active == True
        ).first()
    else:
        # 获取食材对应的第一个商品（兼容旧行为）
        product = db.query(Product).filter(
            Product.ingredient_id == ingredient_id,
            Product.is_active == True
        ).first()

    if not product:
        return []

    # 查询当天的所有价格记录
    records = db.query(ProductRecord).filter(
        ProductRecord.user_id == user_id,
        ProductRecord.product_id == product.id,
        ProductRecord.recorded_at >= day_start,
        ProductRecord.recorded_at <= day_end
    ).all()

    return records


def _get_ingredient_fallback(db: Session, ingredient: Ingredient, user_id: int, visited: Optional[List[int]] = None) -> Optional[tuple[Ingredient, ProductRecord, str]]:
    """
    获取食材的回退链中的第一个有价格的食材

    Args:
        db: 数据库会话
        ingredient: 食材对象
        user_id: 用户ID
        visited: 已访问的食材ID列表（避免循环）

    Returns:
        (fallback_ingredient, price_record, fallback_chain) 或 None
        - fallback_ingredient: 回退食材对象
        - price_record: 价格记录
        - fallback_chain: 回退链描述（如 "猪肉 → 里脊"）
    """
    if not ingredient:
        return None

    # 防止循环引用
    if visited is None:
        visited = []

    if ingredient.id in visited:
        return None

    visited = visited + [ingredient.id]

    # 查找所有回退父级（可能有多个，按 strength 降序尝试）
    hierarchies = db.query(IngredientHierarchy).filter(
        IngredientHierarchy.child_id == ingredient.id,
        IngredientHierarchy.relation_type == HierarchyRelationType.FALLBACK.value
    ).order_by(IngredientHierarchy.strength.desc()).all()

    for hierarchy in hierarchies:
        if not hierarchy or not hierarchy.parent:
            continue

        # 检查回退父级是否有价格
        product = db.query(Product).filter(
            Product.ingredient_id == hierarchy.parent.id,
            Product.is_active == True
        ).first()

        if product:
            # 查找用户是否有该商品的价格记录
            latest_record = db.query(ProductRecord).filter(
                ProductRecord.user_id == user_id,
                ProductRecord.product_id == product.id
            ).order_by(ProductRecord.recorded_at.desc()).first()

            if latest_record:
                # 找到了有价格的回退食材
                fallback_chain = f"{ingredient.name} → {hierarchy.parent.name}"
                return hierarchy.parent, latest_record, fallback_chain

        # 如果当前回退父级没有价格，继续向上查找
        result = _get_ingredient_fallback(db, hierarchy.parent, user_id, visited)
        if result:
            fallback_ingredient, price_record, chain = result
            # 在回退链的开头添加当前食材
            fallback_chain = f"{ingredient.name} → {chain}"
            return fallback_ingredient, price_record, fallback_chain

    return None


def _get_ingredient_nutrition(
    db: Session,
    ingredient: Ingredient,
    visited: Optional[List[int]] = None
) -> Optional[tuple[Ingredient, NutritionData, str]]:
    """
    获取食材的回退链中的第一个有营养数据的食材

    Args:
        db: 数据库会话
        ingredient: 食材对象
        visited: 已访问的食材ID列表（避免循环）

    Returns:
        (fallback_ingredient, nutrition_data, fallback_chain) 或 None
        - fallback_ingredient: 回退食材对象
        - nutrition_data: 营养数据
        - fallback_chain: 回退链描述（如 "猪肉 → 里脊"）
    """
    if not ingredient:
        return None

    # 防止循环引用
    if visited is None:
        visited = []

    if ingredient.id in visited:
        return None

    visited = visited + [ingredient.id]

    # 查找所有回退父级（可能有多个，按 strength 降序尝试）
    hierarchies = db.query(IngredientHierarchy).filter(
        IngredientHierarchy.child_id == ingredient.id,
        IngredientHierarchy.relation_type == HierarchyRelationType.FALLBACK.value
    ).order_by(IngredientHierarchy.strength.desc()).all()

    for hierarchy in hierarchies:
        if not hierarchy or not hierarchy.parent:
            continue

        # 检查回退父级是否有营养数据
        nutrition = db.query(NutritionData).filter(
            NutritionData.ingredient_id == hierarchy.parent.id
        ).order_by(NutritionData.id.desc()).first()

        if nutrition:
            # 找到了有营养数据的回退食材
            fallback_chain = f"{ingredient.name} → {hierarchy.parent.name}"
            return hierarchy.parent, nutrition, fallback_chain

        # 如果当前回退父级没有营养数据，继续向上查找
        result = _get_ingredient_nutrition(db, hierarchy.parent, visited)
        if result:
            fallback_ingredient, nutrition_data, chain = result
            # 在回退链的开头添加当前食材
            fallback_chain = f"{ingredient.name} → {chain}"
            return fallback_ingredient, nutrition_data, fallback_chain

    return None


async def batch_calculate_recipes_cost_nutrition(
    recipe_ids: List[int],
    user_id: int,
    db: Session = None
) -> Dict[int, Dict]:
    """批量计算多个菜谱的成本和营养信息"""
    # 首先获取所有菜谱
    recipes = db.query(Recipe).filter(Recipe.id.in_(recipe_ids)).all()

    results = {}

    for recipe in recipes:
        cost_result = await calculate_recipe_cost(recipe.id, user_id, db)
        nutrition_result = await calculate_recipe_nutrition(recipe.id, db)

        # 合并结果
        combined_result = {
            "cost": cost_result,
            "nutrition": nutrition_result
        }

        results[recipe.id] = combined_result

    return results


def _get_effective_quantity(recipe_ingredient) -> Decimal:
    """
    从 recipe_ingredient 中提取有效数量。
    优先使用 quantity，如果为 None 则尝试从 quantity_range 取平均值。
    """
    qty = recipe_ingredient.quantity

    # 如果 quantity 为 None 或字符串 "None"，检查 quantity_range
    if qty is None or (isinstance(qty, str) and qty.lower() == "none"):
        q_range = recipe_ingredient.quantity_range
        if q_range is not None and q_range != 'null':
            try:
                if isinstance(q_range, str):
                    q_range = json.loads(q_range)
                if isinstance(q_range, dict):
                    q_min = q_range.get("min")
                    q_max = q_range.get("max")
                    if q_max is not None:
                        return Decimal(str(q_max))
                    elif q_min is not None:
                        return Decimal(str(q_min))
                    elif q_max is not None:
                        return Decimal(str(q_max))
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        return Decimal("0")

    return Decimal(str(qty))


async def calculate_recipe_cost(
    recipe_id: int,
    user_id: int,
    db: Session = None
) -> Dict:
    """计算菜谱成本，使用当天价格区间的平均值"""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        return None

    total_cost = Decimal("0.00")
    cost_breakdown = []

    # 获取当前日期
    now = datetime.now()

    for recipe_ingredient in recipe.ingredients:
        ingredient = recipe_ingredient.ingredient

        # 检查食材是否已被合并，如果是，使用合并后的目标食材
        if ingredient and ingredient.is_merged and ingredient.merged_into_id:
            # 获取合并后的目标食材
            ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient.merged_into_id).first()

        if not ingredient:
            continue

        # 通过ingredient_id查找所有关联商品（可能有多个品牌商品）
        from app.models.product_entity import Product
        products = db.query(Product).filter(
            Product.ingredient_id == ingredient.id,
            Product.is_active == True
        ).all()

        day_records = []
        unit_price = None
        fallback_chain = None  # 回退链信息
        original_ingredient_name = ingredient.name  # 保存原始食材名称
        product = None

        # 遍历所有商品，找到第一个有价格记录的
        if products:
            for p in products:
                day_records = _get_price_records_for_date(db, user_id, ingredient.id, now, product_id=p.id)
                if day_records:
                    product = p
                    break

            # 如果所有商品都没有当天记录，使用前向填充（遍历所有商品查找最近的记录）
            if not day_records:
                # 先尝试使用食材回退机制
                fallback_result = _get_ingredient_fallback(db, ingredient, user_id)
                if fallback_result:
                    fallback_ingredient, fallback_price_record, fallback_chain = fallback_result
                    # 查找回退食材的商品
                    fallback_products = db.query(Product).filter(
                        Product.ingredient_id == fallback_ingredient.id,
                        Product.is_active == True
                    ).all()

                    if fallback_products:
                        # 查找回退食材当天的价格记录（遍历所有商品）
                        for fp in fallback_products:
                            day_records = _get_price_records_for_date(db, user_id, fallback_ingredient.id, now, product_id=fp.id)
                            if day_records:
                                product = fp
                                break

                        # 如果回退食材也没有当天记录，使用前向填充
                        if not day_records:
                            for fp in fallback_products:
                                fallback_record = _get_price_record_with_fallback(
                                    db=db,
                                    user_id=user_id,
                                    product_id=fp.id,
                                    as_of_date=now
                                )
                                if fallback_record:
                                    day_records = [fallback_record]
                                    product = fp
                                    break
                            if day_records:
                                ingredient = fallback_ingredient
                        else:
                            ingredient = fallback_ingredient

                # 如果食材回退也没有，使用原食材前向填充（遍历所有商品）
                if not day_records and products:
                    for p in products:
                        fallback_record = _get_price_record_with_fallback(
                            db=db,
                            user_id=user_id,
                            product_id=p.id,
                            as_of_date=now
                        )
                        if fallback_record:
                            day_records = [fallback_record]
                            product = p
                            break
        else:
            # 如果找不到商品，尝试使用回退食材
            fallback_result = _get_ingredient_fallback(db, ingredient, user_id)
            if fallback_result:
                fallback_ingredient, fallback_price_record, fallback_chain = fallback_result
                # 查找回退食材的所有商品
                fallback_products = db.query(Product).filter(
                    Product.ingredient_id == fallback_ingredient.id,
                    Product.is_active == True
                ).all()

                if fallback_products:
                    # 遍历所有商品，查找当天的价格记录
                    for fp in fallback_products:
                        day_records = _get_price_records_for_date(db, user_id, fallback_ingredient.id, now, product_id=fp.id)
                        if day_records:
                            break

                    # 如果回退食材也没有当天记录，使用前向填充（遍历所有商品）
                    if not day_records:
                        for fp in fallback_products:
                            fallback_record = _get_price_record_with_fallback(
                                db=db,
                                user_id=user_id,
                                product_id=fp.id,
                                as_of_date=now
                            )
                            if fallback_record:
                                day_records = [fallback_record]
                                break

                    ingredient = fallback_ingredient

            # 如果仍然没有记录，尝试通过名称匹配
            if not day_records:
                latest_record = db.query(ProductRecord).filter(
                    ProductRecord.user_id == user_id,
                    ProductRecord.product_name.contains(original_ingredient_name)
                ).order_by(ProductRecord.recorded_at.desc()).first()

                if latest_record:
                    day_records = [latest_record]

        if day_records:
            # 计算当天所有记录的平均单价
            unit_prices = []
            for record in day_records:
                record_price = Decimal(str(record.price))
                std_qty = record.standard_quantity
                if std_qty is None or std_qty == 0:
                    unit_price_temp = record_price
                else:
                    record_quantity = Decimal(str(std_qty))
                    unit_price_temp = record_price / record_quantity
                unit_prices.append(unit_price_temp)

            # 使用平均单价
            if unit_prices:
                unit_price = sum(unit_prices) / len(unit_prices)

        if unit_price is not None:
            # 计算成本：单价 × 菜谱中的数量 = 成本
            # 优先使用 quantity，如果为 None 则从 quantity_range 取平均值
            quantity = _get_effective_quantity(recipe_ingredient)

            # 只有当数量大于0时才计算成本
            # 对于数量为0的食材，不计入成本（但可能需要显示在成本明细中）
            if quantity:
                try:
                    cost = unit_price * quantity if unit_price else Decimal("0")
                    total_cost += cost

                    cost_breakdown.append({
                        "ingredient_name": ingredient.name,
                        "original_ingredient_name": original_ingredient_name,  # 添加原始食材名称
                        "ingredient_id": ingredient.id,
                        "recipe_ingredient_id": recipe_ingredient.id,  # 添加recipe_ingredient的ID
                        "quantity": str(quantity),
                        "unit_price": float(unit_price) if unit_price else 0.0,
                        "cost": float(cost),
                        "fallback_chain": fallback_chain  # 回退链信息（如果有）
                    })
                except Exception as e:
                    # 数量解析失败，使用基础价格
                    cost = unit_price
                    total_cost += cost
                    cost_breakdown.append({
                        "ingredient_name": ingredient.name,
                        "ingredient_id": ingredient.id,
                        "recipe_ingredient_id": recipe_ingredient.id,  # 添加recipe_ingredient的ID
                        "quantity": "1",  # 默认为1
                        "unit_price": float(unit_price) if unit_price else 0.0,
                        "cost": float(cost),
                        "fallback_chain": fallback_chain  # 回退链信息（如果有）
                    })
            else:
                # 对于数量为0的食材，我们仍然添加到明细中但成本为0
                # 这样用户可以看到所有食材，即使它们的数量为0
                cost_breakdown.append({
                    "ingredient_name": ingredient.name,
                    "original_ingredient_name": original_ingredient_name,  # 添加原始食材名称
                    "ingredient_id": ingredient.id,
                    "recipe_ingredient_id": recipe_ingredient.id,  # 添加recipe_ingredient的ID
                    "quantity": str(quantity),
                    "unit_price": float(unit_price) if unit_price else 0.0,
                    "cost": 0.0,
                    "fallback_chain": fallback_chain  # 回退链信息（如果有）
                })

    return {
        "total_cost": total_cost,
        "currency": "CNY",
        "cost_per_serving": total_cost / (recipe.servings or 1),
        "cost_breakdown": cost_breakdown
    }


def calculate_recipe_cost_range_as_of(
    recipe_id: int,
    user_id: int,
    as_of_date: datetime,
    db: Session
) -> Dict:
    """
    计算菜谱在指定日期的成本区间

    Args:
        recipe_id: 菜谱ID
        user_id: 用户ID
        as_of_date: 指定日期
        db: 数据库会话

    Returns:
        成本区间数据，包含 min_cost, max_cost, avg_cost（单位：元）
    """
    from app.models.product_entity import Product

    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        return None

    total_min_cost = Decimal("0.00")
    total_max_cost = Decimal("0.00")
    total_avg_cost = Decimal("0.00")
    valid_ingredients = 0

    # 获取菜谱中的所有食材（包括可选食材）
    for recipe_ingredient in recipe.ingredients:
        ingredient = recipe_ingredient.ingredient

        # 检查食材是否已被合并，如果是，使用合并后的目标食材
        if ingredient and ingredient.is_merged and ingredient.merged_into_id:
            ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient.merged_into_id).first()

        if not ingredient:
            continue

        # 获取食材对应的所有商品（可能有多个品牌商品）
        products = db.query(Product).filter(
            Product.ingredient_id == ingredient.id,
            Product.is_active == True
        ).all()

        if not products:
            continue

        # 遍历所有商品，查找当天有价格记录的商品
        day_records = []
        product = None
        for p in products:
            day_records = _get_price_records_for_date(db, user_id, ingredient.id, as_of_date, product_id=p.id)
            if day_records:
                product = p
                break

        # 如果当天无记录，使用前向填充
        if not day_records:
            # 先尝试使用食材回退机制
            fallback_result = _get_ingredient_fallback(db, ingredient, user_id)
            if fallback_result:
                fallback_ingredient, fallback_price_record, fallback_chain = fallback_result
                # 查找回退食材的所有商品
                fallback_products = db.query(Product).filter(
                    Product.ingredient_id == fallback_ingredient.id,
                    Product.is_active == True
                ).all()

                if fallback_products:
                    # 遍历回退食材的所有商品，查找价格记录
                    for fp in fallback_products:
                        fallback_record = _get_price_record_with_fallback(
                            db=db,
                            user_id=user_id,
                            product_id=fp.id,
                            as_of_date=as_of_date
                        )
                        if fallback_record:
                            day_records = [fallback_record]
                            break

            # 如果食材回退也没有，使用原食材前向填充（遍历所有商品）
            if not day_records and products:
                for p in products:
                    fallback_record = _get_price_record_with_fallback(
                        db=db,
                        user_id=user_id,
                        product_id=p.id,
                        as_of_date=as_of_date
                    )
                    if fallback_record:
                        day_records = [fallback_record]
                        product = p
                        break

        # 如果仍然没有记录，跳过该食材
        if not day_records:
            continue

        # 计算当天的单价列表
        unit_prices = []
        for record in day_records:
            record_price = Decimal(str(record.price))
            std_qty = record.standard_quantity
            if std_qty is None or std_qty == 0:
                unit_price = record_price
            else:
                record_quantity = Decimal(str(std_qty))
                unit_price = record_price / record_quantity
            unit_prices.append(unit_price)

        if not unit_prices:
            continue

        # 计算统计值
        min_unit_price = min(unit_prices)
        max_unit_price = max(unit_prices)
        avg_unit_price = sum(unit_prices) / len(unit_prices)

        # 计算该食材的成本
        quantity = _get_effective_quantity(recipe_ingredient)

        if quantity:
            try:
                ingredient_min_cost = min_unit_price * quantity
                ingredient_max_cost = max_unit_price * quantity
                ingredient_avg_cost = avg_unit_price * quantity

                total_min_cost += ingredient_min_cost
                total_max_cost += ingredient_max_cost
                total_avg_cost += ingredient_avg_cost
                valid_ingredients += 1
            except Exception as e:
                # 数量解析失败，跳过该食材
                continue

    return {
        "min_cost": float(total_min_cost),
        "max_cost": float(total_max_cost),
        "avg_cost": float(total_avg_cost),
        "currency": "CNY",
        "valid_ingredients": valid_ingredients
    }


def calculate_recipe_cost_range_trend(
    recipe_id: int,
    user_id: int,
    db: Session,
    days: int = 90
) -> List[Dict]:
    """
    计算菜谱的成本区间趋势（批量优化版）

    遍历指定日期范围，对于每一天，计算菜谱在该日期的成本区间。
    批量预加载所有食材、商品、价格记录和回退关系，避免逐天逐食材查询数据库。

    Args:
        recipe_id: 菜谱ID
        user_id: 用户ID
        db: 数据库会话
        days: 查询天数（默认90天）

    Returns:
        成本区间趋势数据列表，每条记录包含：
        - date: 日期 (YYYY-MM-DD)
        - recorded_at: Unix 时间戳（秒）
        - min_cost: 最小成本（元）
        - max_cost: 最大成本（元）
        - avg_cost: 平均成本（元）
    """
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        return []

    # 获取最早的价格记录日期
    earliest_record = db.query(ProductRecord).filter(
        ProductRecord.user_id == user_id
    ).order_by(ProductRecord.recorded_at.asc()).first()

    if not earliest_record:
        return []

    # 确定日期范围
    end_date = datetime.now().date()
    start_date = max(earliest_record.recorded_at.date(), end_date - timedelta(days=days))

    # ========== 批量预加载所有数据 ==========

    # 1. 收集所有有效食材ID（处理合并）
    ingredient_ids = set()
    ri_list = list(recipe.ingredients)
    ri_ingredient_map = {}  # recipe_ingredient_id -> (ingredient, original_name_for_fallback)

    for ri in ri_list:
        ing = ri.ingredient
        if ing and ing.is_merged and ing.merged_into_id:
            ing = db.query(Ingredient).filter(Ingredient.id == ing.merged_into_id).first()
        if ing:
            ingredient_ids.add(ing.id)
            ri_ingredient_map[ri.id] = ing

    if not ingredient_ids:
        return []

    # 2. 批量加载所有商品
    all_products = db.query(Product).filter(
        Product.ingredient_id.in_(list(ingredient_ids)),
        Product.is_active == True
    ).all()

    products_by_ingredient = defaultdict(list)
    all_product_ids = set()
    for p in all_products:
        products_by_ingredient[p.ingredient_id].append(p)
        all_product_ids.add(p.id)

    if not all_product_ids:
        return []

    # 3. 批量加载所有价格记录（按 product_id 升序、recorded_at 升序排列）
    all_records = db.query(ProductRecord).filter(
        ProductRecord.user_id == user_id,
        ProductRecord.product_id.in_(list(all_product_ids))
    ).order_by(ProductRecord.product_id, ProductRecord.recorded_at.asc()).all()

    records_by_product = defaultdict(list)
    for r in all_records:
        records_by_product[r.product_id].append(r)

    # 4. 批量加载所有回退关系（按 strength 降序排列）
    all_fallbacks = db.query(IngredientHierarchy).filter(
        IngredientHierarchy.relation_type == HierarchyRelationType.FALLBACK.value
    ).order_by(IngredientHierarchy.strength.desc()).all()

    fallback_by_child = defaultdict(list)
    for f in all_fallbacks:
        fallback_by_child[f.child_id].append(f)

    # 5. 构建价格源缓存：为每个食材找到最佳价格源（商品ID + 价格记录列表）
    price_source_cache = {}  # ingredient_id -> (product_id, records_list)

    def _find_price_source(ing_id: int, visited: Optional[set] = None):
        """在内存中查找食材的最佳价格源（替代 _get_ingredient_fallback 的数据库查询）"""
        if visited is None:
            visited = set()
        if ing_id in visited:
            return None
        visited.add(ing_id)

        if ing_id in price_source_cache:
            return price_source_cache[ing_id]

        # 尝试直接商品
        for p in products_by_ingredient.get(ing_id, []):
            if p.id in records_by_product and records_by_product[p.id]:
                result = (p.id, records_by_product[p.id])
                price_source_cache[ing_id] = result
                return result

        # 尝试回退父级
        for f in fallback_by_child.get(ing_id, []):
            if f.parent_id:
                result = _find_price_source(f.parent_id, visited)
                if result:
                    price_source_cache[ing_id] = result
                    return result

        return None

    # 计算每个食材的价格源
    for ing_id in ingredient_ids:
        _find_price_source(ing_id)

    # ========== 逐天计算 ==========

    import bisect

    # 生成日期列表
    date_list = []
    current_date = start_date
    while current_date <= end_date:
        date_list.append(current_date)
        current_date += timedelta(days=1)

    cost_range_trend = []
    for date in date_list:
        as_of_datetime = datetime.combine(date, datetime.max.time()) - timedelta(seconds=1)

        total_min_cost = Decimal("0.00")
        total_max_cost = Decimal("0.00")
        total_avg_cost = Decimal("0.00")
        valid_ingredients = 0

        for ri in ri_list:
            ing = ri_ingredient_map.get(ri.id)
            if not ing:
                continue

            source = price_source_cache.get(ing.id)
            if not source:
                continue

            product_id, records = source

            # 二分查找截至 as_of_datetime 的最新记录
            record_dates = [r.recorded_at for r in records]
            idx = bisect.bisect_right(record_dates, as_of_datetime) - 1
            if idx < 0:
                # 没有截至该日期的记录，使用最早记录（前向填充）
                latest_record = records[0]
            else:
                latest_record = records[idx]

            # 计算单价
            record_price = Decimal(str(latest_record.price))
            std_qty = latest_record.standard_quantity
            if std_qty is None or std_qty == 0:
                unit_price = record_price
            else:
                unit_price = record_price / Decimal(str(std_qty))

            # 计算该食材成本
            quantity = _get_effective_quantity(ri)
            if not quantity:
                continue

            try:
                ingredient_cost = unit_price * quantity
                total_min_cost += ingredient_cost
                total_max_cost += ingredient_cost
                total_avg_cost += ingredient_cost
                valid_ingredients += 1
            except Exception:
                continue

        if total_avg_cost > 0:
            recorded_at_dt = datetime.combine(date, datetime.min.time()) + timedelta(hours=12)
            recorded_at = int(recorded_at_dt.timestamp())

            cost_range_trend.append({
                "date": date.strftime("%Y-%m-%d"),
                "recorded_at": recorded_at,
                "min_cost": float(total_min_cost),
                "max_cost": float(total_max_cost),
                "avg_cost": float(total_avg_cost)
            })

    return cost_range_trend


async def calculate_recipe_nutrition(
    recipe_id: int,
    db: Session = None
) -> Dict:
    """计算菜谱营养"""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        return None

    # NRV（营养素参考值）- 中国标准值（成人每日摄入量）
    # 来源：GB 28050-2011《食品安全国家标准 预包装食品营养标签通则》
    NRV_REFERENCE_VALUES = {
        "能量": 2000,  # kcal
        "蛋白质": 60,   # g
        "脂肪": 60,     # g
        "碳水化合物": 300,  # g
        "膳食纤维": 25,   # g
        "钙": 800,      # mg
        "铁": 15,       # mg
        "钠": 2000,     # mg
        "钾": 2000,     # mg
        "维生素A": 800,  # μg
        "维生素C": 100,   # mg
        "维生素B1": 1.2, # mg
        "维生素B2": 1.4, # mg
        "维生素B12": 2.4, # μg
        "维生素D": 5,     # μg
        "维生素E": 14,    # mg
        "维生素K": 80     # μg
    }

    # 初始化所有核心营养素的总量
    total_core_nutrients = {
        "能量": {"value": 0, "unit": "kcal", "key": "energy_kcal"},
        "蛋白质": {"value": 0, "unit": "g", "key": "protein"},
        "脂肪": {"value": 0, "unit": "g", "key": "fat"},
        "碳水化合物": {"value": 0, "unit": "g", "key": "carbohydrate"},
        "膳食纤维": {"value": 0, "unit": "g", "key": "fiber"},
        "钙": {"value": 0, "unit": "mg", "key": "calcium"},
        "铁": {"value": 0, "unit": "mg", "key": "iron"},
        "钠": {"value": 0, "unit": "mg", "key": "sodium"},
        "钾": {"value": 0, "unit": "mg", "key": "potassium"},
        "维生素A": {"value": 0, "unit": "μg", "key": "vitamin_a_rae"},
        "维生素C": {"value": 0, "unit": "mg", "key": "vitamin_c"},
        "维生素B1": {"value": 0, "unit": "mg", "key": "vitamin_b1"},
        "维生素B2": {"value": 0, "unit": "mg", "key": "vitamin_b2"},
        "维生素B12": {"value": 0, "unit": "μg", "key": "vitamin_b12"},
        "维生素D": {"value": 0, "unit": "μg", "key": "vitamin_d"},
        "维生素E": {"value": 0, "unit": "mg", "key": "vitamin_e"},
        "维生素K": {"value": 0, "unit": "μg", "key": "vitamin_k"}
    }

    from app.utils.unit_converter import convert_to_standard

    # 存储食材贡献详情
    ingredient_details = []

    # 初始化所有营养素的总量（包括 all_nutrients）
    total_all_nutrients = {}

    for recipe_ingredient in recipe.ingredients:
        ingredient = recipe_ingredient.ingredient

        # 检查食材是否已被合并，如果是，使用合并后的目标食材
        if ingredient and ingredient.is_merged and ingredient.merged_into_id:
            ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient.merged_into_id).first()

        if not ingredient:
            continue

        # 使用 ingredient_id 查找营养数据（而不是 nutrition_id）
        nutrition = db.query(NutritionData).filter(
            NutritionData.ingredient_id == ingredient.id
        ).order_by(NutritionData.id.desc()).first()

        # 如果当前食材没有营养数据，尝试使用回退食材
        if not nutrition:
            fallback_result = _get_ingredient_nutrition(db, ingredient, None)
            if fallback_result:
                fallback_ingredient, fallback_nutrition, fallback_chain = fallback_result
                ingredient = fallback_ingredient
                nutrition = fallback_nutrition
                # 记录使用了回退食材
                fallback_chain_info = fallback_chain
            else:
                continue
        else:
            fallback_chain_info = None

        # 获取营养数据（从 JSON 字段）
        nutrients = nutrition.nutrients or {}
        core_nutrients = nutrients.get("core_nutrients", {})
        all_nutrients = nutrients.get("all_nutrients", {})

        # 获取回退食材的营养数据（用于单条营养素回退）
        fallback_nutrition = None
        if not fallback_chain_info:
            # 如果已经使用了回退食材（fallback_chain_info 不为 None），就不需要再次查找
            fallback_result = _get_ingredient_nutrition(db, ingredient, None)
            if fallback_result:
                fallback_nutrition = fallback_result[1]
                if fallback_nutrition and fallback_nutrition.nutrients:
                    fallback_nutrients = fallback_nutrition.nutrients.get("core_nutrients", {})
                else:
                    fallback_nutrients = {}
            else:
                fallback_nutrients = {}

        # 提取参考基准
        reference_amount = Decimal(str(nutrition.reference_amount or 100.0))
        reference_unit = nutrition.reference_unit or "g"

        # 获取菜谱中的原料数量，并转换为标准单位
        ingredient_quantity_str = recipe_ingredient.quantity or "0"
        # 将 None 视为 "0"
        if recipe_ingredient.quantity is None:
            ingredient_quantity_str = "0"
        ingredient_unit = ""

        # 尝试解析数量和单位
        try:
            # 如果数量是纯数字字符串
            if str(ingredient_quantity_str).replace(".", "").replace("-", "").isdigit():
                quantity = Decimal(str(ingredient_quantity_str))
                # 如果有单位信息，尝试使用原始数量和单位
                if recipe_ingredient.unit:
                    ingredient_unit = recipe_ingredient.unit.abbreviation
                    # 转换为标准单位
                    standard_quantity, standard_unit = convert_to_standard(quantity, ingredient_unit)
                else:
                    # 没有单位信息，假设使用参考基准单位
                    standard_quantity = quantity
                    standard_unit = reference_unit
            else:
                # 数量可能包含单位（如 "250g"），需要解析
                import re
                match = re.match(r"([\d.]+)\s*([a-zA-Z\u4e00-\u9fff]+)", str(ingredient_quantity_str))
                if match:
                    quantity = Decimal(match.group(1))
                    ingredient_unit = match.group(2)
                    standard_quantity, standard_unit = convert_to_standard(quantity, ingredient_unit)
                else:
                    # 无法解析，使用默认值
                    standard_quantity = Decimal("0")
                    standard_unit = reference_unit
        except Exception as e:
            # 解析失败，使用默认值
            standard_quantity = Decimal("0")
            standard_unit = reference_unit

        # 计算比例因子（菜谱中的数量 / 参考基准数量）
        # 确保单位一致才能比较

        # 首先处理容量单位的密度转换
        if standard_unit.lower() == "ml" and recipe_ingredient.unit:
            # 如果是容量单位，尝试使用密度转换为重量
            from app.models.ingredient_density import IngredientDensity

            # 查找密度数据（mL → g）
            density = db.query(IngredientDensity).filter(
                IngredientDensity.ingredient_id == ingredient.id,
                IngredientDensity.from_unit_id == recipe_ingredient.unit.id,
                IngredientDensity.to_unit_id == 3  # g 的 ID
            ).first()

            if density and density.density_value:
                # 使用密度转换：重量 = 容量 × 密度
                standard_quantity = standard_quantity * Decimal(str(density.density_value))
                standard_unit = "g"  # 转换为克
            else:
                # 没有密度数据，假设密度为 1.0 g/mL
                standard_quantity = standard_quantity
                standard_unit = "g"

        if standard_unit.lower() in ["g", "ml"] and reference_unit.lower() in ["g", "ml"]:
            # 如果都是重量或容量单位，可以计算比例
            ratio = standard_quantity / reference_amount
        elif recipe_ingredient.unit and recipe_ingredient.unit.unit_type == "count":
            # 如果是计数单位（如"个"），尝试使用 piece_weight 转换
            if ingredient.piece_weight and ingredient.piece_weight_unit_id:
                # 使用食材的标准重量转换（如：1个鸡蛋=50g）
                piece_weight = Decimal(str(ingredient.piece_weight))
                piece_weight_unit = ingredient.piece_weight_unit.abbreviation

                # 转换为标准重量单位
                converted_weight, converted_unit = convert_to_standard(piece_weight, piece_weight_unit)
                # 计算总重量（数量 × 每个的重量）
                total_weight = quantity * converted_weight

                if converted_unit.lower() == reference_unit.lower():
                    # 单位一致，计算比例
                    ratio = total_weight / reference_amount
                else:
                    # 单位不一致，尝试转换
                    from app.models.unit import Unit
                    weight_unit_obj = db.query(Unit).filter(Unit.abbreviation == converted_unit).first()
                    if weight_unit_obj and weight_unit_obj.unit_type == "mass":
                        ratio = total_weight / reference_amount
                    else:
                        # 无法转换，使用默认值
                        ratio = Decimal("1.0")
            else:
                # 没有设置标准重量，假设比例是1:1
                ratio = Decimal("1.0")
        else:
            # 单位不一致，假设比例是1:1（使用参考值）
            ratio = Decimal("1.0")

        # 累加所有核心营养素值
        for nutrient_name, nutrient_data in core_nutrients.items():
            if nutrient_name in total_core_nutrients:
                # 确保 value 不为 None
                value = float(nutrient_data.get("value", 0) or 0)
                source_unit = nutrient_data.get("unit", "")

                # 如果值为 0 且有回退食材，尝试从回退食材获取该营养素的值
                if value == 0 and fallback_nutrients and nutrient_name in fallback_nutrients:
                    fallback_value = float(fallback_nutrients[nutrient_name].get("value", 0) or 0)
                    if fallback_value > 0:
                        value = fallback_value
                        source_unit = fallback_nutrients[nutrient_name].get("unit", "")
                        # 记录使用了回退值（可在日志中查看）

                # 如果是能量，检查单位并转换为 kcal
                if nutrient_name == "能量" and source_unit in ("kJ", "千焦", "千焦(kJ)"):
                    # 先将 kJ 转换为 kcal（1 kJ = 0.239006 kcal）
                    value_kcal = value * 0.239006
                    total_core_nutrients[nutrient_name]["value"] += value_kcal * float(ratio)
                    total_core_nutrients[nutrient_name]["unit"] = "kcal"
                else:
                    total_core_nutrients[nutrient_name]["value"] += value * float(ratio)
                    total_core_nutrients[nutrient_name]["unit"] = source_unit

        # 累加所有其他营养素值（all_nutrients）
        for nutrient_name, nutrient_data in all_nutrients.items():
            if nutrient_name not in total_core_nutrients:  # 避免重复累加核心营养素
                # 确保 value 不为 None
                value = float(nutrient_data.get("value", 0) or 0)
                source_unit = nutrient_data.get("unit", "")

                # 如果值为 0 且有回退食材，尝试从回退食材获取该营养素的值
                if value == 0 and fallback_nutrients and nutrient_name in fallback_nutrients:
                    fallback_value = float(fallback_nutrients[nutrient_name].get("value", 0) or 0)
                    if fallback_value > 0:
                        value = fallback_value
                        source_unit = fallback_nutrients[nutrient_name].get("unit", "")

                # 初始化 total_all_nutrients（如果不存在）
                if nutrient_name not in total_all_nutrients:
                    total_all_nutrients[nutrient_name] = {"value": 0, "unit": source_unit}

                # 如果是能量，检查单位并转换为 kcal
                if nutrient_name == "能量" and source_unit in ("kJ", "千焦", "千焦(kJ)"):
                    # 先将 kJ 转换为 kcal（1 kJ = 0.239006 kcal）
                    value_kcal = value * 0.239006
                    total_all_nutrients[nutrient_name]["value"] += value_kcal * float(ratio)
                    total_all_nutrients[nutrient_name]["unit"] = "kcal"
                else:
                    total_all_nutrients[nutrient_name]["value"] += value * float(ratio)
                    total_all_nutrients[nutrient_name]["unit"] = source_unit

        # 添加食材贡献详情
        # 收集每个营养素的贡献值（考虑回退）
        contribution_data = {}
        for nutrient_name, nutrient_data in core_nutrients.items():
            if nutrient_name in total_core_nutrients:
                value = float(nutrient_data.get("value", 0) or 0)
                used_fallback = False  # 标记是否使用了回退

                # 如果值为 0 且有回退食材，尝试从回退食材获取该营养素的值
                if value == 0 and fallback_nutrients and nutrient_name in fallback_nutrients:
                    fallback_value = float(fallback_nutrients[nutrient_name].get("value", 0) or 0)
                    if fallback_value > 0:
                        value = fallback_value
                        used_fallback = True

                contribution_data[nutrient_name] = {
                    "value": value * float(ratio),
                    "unit": nutrient_data.get("unit", ""),
                    "nrp_pct": round((value * float(ratio) / NRV_REFERENCE_VALUES.get(nutrient_name, 1)) * 100, 2) if NRV_REFERENCE_VALUES.get(nutrient_name, 0) > 0 else 0,
                    "used_fallback": used_fallback  # 标记是否使用了回退
                }

        ingredient_details.append({
            "recipe_ingredient_id": recipe_ingredient.id,  # 添加recipe_ingredient的ID
            "ingredient_id": ingredient.id,
            "ingredient_name": ingredient.name,
            "quantity": float(standard_quantity),
            "unit": standard_unit,
            "nutrition_contribution": contribution_data
        })

    servings = recipe.servings or 1

    # 计算每份营养值和 NRV 百分比
    per_serving_core_nutrients = {}
    for name, data in total_core_nutrients.items():
        # 处理 None 值的情况
        total_value = data["value"] if data["value"] is not None else 0
        per_serving_value = round(total_value / servings, 2)
        per_serving_unit = data["unit"] if data["unit"] is not None else ""

        # 使用 NRV 标准参考值计算 NRV 百分比
        nrv_reference = NRV_REFERENCE_VALUES.get(name, 0)
        if nrv_reference > 0:
            # NRV 百分比 = （每份营养值 / NRV 标准值）× 100
            per_serving_nrp_pct = round((per_serving_value / nrv_reference) * 100, 2)
            # 添加参考值说明
            per_serving_standard = f"NRV标准值：{nrv_reference}{per_serving_unit}"
        else:
            # 没有参考值，设为 None
            per_serving_nrp_pct = None
            per_serving_standard = "无标准"

        per_serving_core_nutrients[name] = {
            "value": per_serving_value,
            "unit": per_serving_unit,
            "key": data["key"],
            "nrp_pct": per_serving_nrp_pct,
            "standard": per_serving_standard
        }

    # 计算每份的 all_nutrients 值
    per_serving_all_nutrients = {}
    for name, data in total_all_nutrients.items():
        # 处理 None 值的情况
        total_value = data["value"] if data["value"] is not None else 0
        per_serving_value = round(total_value / servings, 2)
        per_serving_unit = data["unit"] if data["unit"] is not None else ""

        # 使用 NRV 标准参考值计算 NRV 百分比（如果有参考值）
        nrv_reference = NRV_REFERENCE_VALUES.get(name, 0)
        if nrv_reference > 0:
            per_serving_nrp_pct = round((per_serving_value / nrv_reference) * 100, 2)
            # 添加参考值说明
            per_serving_standard = f"NRV标准值：{nrv_reference}{per_serving_unit}"
        else:
            # 没有参考值，设为 None
            per_serving_nrp_pct = None
            per_serving_standard = "无标准"

        per_serving_all_nutrients[name] = {
            "value": per_serving_value,
            "unit": per_serving_unit,
            "nrp_pct": per_serving_nrp_pct,
            "standard": per_serving_standard
        }

    # 提取简化的核心值用于兼容性
    energy_data = total_core_nutrients.get("能量", {})
    protein_data = total_core_nutrients.get("蛋白质", {})
    fat_data = total_core_nutrients.get("脂肪", {})
    carb_data = total_core_nutrients.get("碳水化合物", {})

    # 如果能量单位是 kJ，转换为 kcal，并处理 None 值
    energy_value = energy_data.get("value", 0) if energy_data else 0
    total_calories = float(energy_value) if energy_value is not None else 0.0
    if energy_data and energy_data.get("unit") in ("kJ", "千焦", "千焦(kJ)"):
        total_calories *= 0.239006

    protein_value = protein_data.get("value", 0) if protein_data else 0.0
    total_protein = float(protein_value) if protein_value is not None else 0.0

    fat_value = fat_data.get("value", 0) if fat_data else 0.0
    total_fat = float(fat_value) if fat_value is not None else 0.0

    carb_value = carb_data.get("value", 0) if carb_data else 0.0
    total_carbs = float(carb_value) if carb_value is not None else 0.0

    return {
        "total_calories": total_calories,
        "total_protein": float(protein_data["value"]),
        "total_fat": float(fat_data["value"]),
        "total_carbs": float(carb_data["value"]),
        "per_serving": {
            "calories": total_calories / servings,
            "protein": total_protein / servings,
            "fat": total_fat / servings,
            "carbs": total_carbs / servings
        },
        "total_nutrition": {
            "core_nutrients": {
                name: {
                    **data,
                    "value": round(data["value"], 2)
                }
                for name, data in total_core_nutrients.items()
            }
        },
        "per_serving_nutrition": {
            "core_nutrients": per_serving_core_nutrients,
            "all_nutrients": per_serving_all_nutrients
        },
        "ingredient_details": ingredient_details  # 添加食材贡献详情
    }


def calculate_recipe_cost_as_of(
    recipe_id: int,
    user_id: int,
    as_of_date: datetime,
    db: Session
) -> Dict:
    """
    计算菜谱在指定日期的成本

    使用截至指定日期的最新价格记录计算成本。
    """
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        return None

    total_cost = Decimal("0.00")
    cost_breakdown = []

    for recipe_ingredient in recipe.ingredients:
        ingredient = recipe_ingredient.ingredient

        # 检查食材是否已被合并，如果是，使用合并后的目标食材
        if ingredient and ingredient.is_merged and ingredient.merged_into_id:
            # 获取合并后的目标食材
            ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient.merged_into_id).first()

        if not ingredient:
            continue

        # 首先通过ingredient_id查找所有商品（可能有多个品牌商品）
        products = db.query(Product).filter(
            Product.ingredient_id == ingredient.id,
            Product.is_active == True
        ).all()

        latest_record = None
        unit_price = None
        fallback_chain = None  # 回退链信息
        original_ingredient_name = ingredient.name  # 保存原始食材名称
        product = None

        if products:
            # 遍历所有商品，找到第一个有价格记录的
            for p in products:
                latest_record = _get_price_record_with_fallback(
                    db=db,
                    user_id=user_id,
                    product_id=p.id,
                    as_of_date=as_of_date
                )
                if latest_record:
                    product = p
                    break

            # 如果找不到价格记录，尝试使用回退食材
            if not latest_record:
                fallback_result = _get_ingredient_fallback(db, ingredient, user_id)
                if fallback_result:
                    fallback_ingredient, fallback_price_record, fallback_chain = fallback_result
                    # 直接使用回退的价格记录
                    latest_record = fallback_price_record
                    # 更新ingredient为回退食材，用于成本计算
                    ingredient = fallback_ingredient

            if latest_record:
                # 计算单价：总价 ÷ 数量
                record_price = Decimal(str(latest_record.price))

                # 修复：检查 standard_quantity 是否为 None 或 0，避免除零错误
                std_qty = latest_record.standard_quantity
                if std_qty is None or std_qty == 0:
                    # 如果标准数量未知，使用原始价格作为单位价格（这种情况很少见）
                    unit_price = record_price
                else:
                    record_quantity = Decimal(str(std_qty))
                    unit_price = record_price / record_quantity
        else:
            # 如果找不到商品，尝试使用回退食材
            fallback_result = _get_ingredient_fallback(db, ingredient, user_id)
            if fallback_result:
                fallback_ingredient, fallback_price_record, fallback_chain = fallback_result
                # 查找回退食材的所有商品
                fallback_products = db.query(Product).filter(
                    Product.ingredient_id == fallback_ingredient.id,
                    Product.is_active == True
                ).all()

                if fallback_products:
                    # 遍历回退食材的所有商品，查找价格记录
                    for fp in fallback_products:
                        latest_record = _get_price_record_with_fallback(
                            db=db,
                            user_id=user_id,
                            product_id=fp.id,
                            as_of_date=as_of_date
                        )
                        if latest_record:
                            product = fp
                            break
                    # 更新ingredient为回退食材
                    ingredient = fallback_ingredient

            if not latest_record:
                # 如果找不到回退食材的价格记录，尝试通过名称匹配（这个SB数据一致性问题）
                # 使用带前向填充机制的价格查找函数
                latest_record = _get_price_record_with_fallback(
                    db=db,
                    user_id=user_id,
                    product_name_contains=original_ingredient_name,
                    as_of_date=as_of_date
                )

            if latest_record:
                # 同样需要计算单价
                record_price = Decimal(str(latest_record.price))

                # 修复：检查 standard_quantity 是否为 None 或 0，避免除零错误
                std_qty = latest_record.standard_quantity
                if std_qty is None or std_qty == 0:
                    # 如果标准数量未知，使用原始价格作为单位价格
                    unit_price = record_price
                else:
                    record_quantity = Decimal(str(std_qty))
                    unit_price = record_price / record_quantity

        if latest_record:
            # 计算成本：单价 × 菜谱中的数量 = 成本
            # 计算成本：单价 × 菜谱中的数量 = 成本
            # 优先使用 quantity，如果为 None 则从 quantity_range 取平均值
            quantity = _get_effective_quantity(recipe_ingredient)

            # 只有当数量大于0时才计算成本
            # 对于数量为0的食材，不计入成本（但可能需要显示在成本明细中）
            if quantity:
                try:
                    cost = unit_price * quantity if unit_price else Decimal("0")
                    total_cost += cost

                    cost_breakdown.append({
                        "ingredient_name": ingredient.name,
                        "original_ingredient_name": original_ingredient_name,  # 添加原始食材名称
                        "ingredient_id": ingredient.id,
                        "recipe_ingredient_id": recipe_ingredient.id,  # 添加recipe_ingredient的ID
                        "quantity": str(quantity),
                        "unit_price": float(unit_price) if unit_price else 0.0,
                        "cost": float(cost),
                        "fallback_chain": fallback_chain  # 回退链信息（如果有）
                    })
                except Exception as e:
                    # 数量解析失败，使用基础价格
                    cost = Decimal(str(latest_record.price))
                    total_cost += cost
                    cost_breakdown.append({
                        "ingredient_name": ingredient.name,
                        "ingredient_id": ingredient.id,
                        "recipe_ingredient_id": recipe_ingredient.id,  # 添加recipe_ingredient的ID
                        "quantity": "1",  # 默认为1
                        "unit_price": float(latest_record.price),
                        "cost": float(cost),
                        "fallback_chain": fallback_chain  # 回退链信息（如果有）
                    })
            else:
                # 对于数量为0的食材，我们仍然添加到明细中但成本为0
                # 这样用户可以看到所有食材，即使它们的数量为0
                cost_breakdown.append({
                    "ingredient_name": ingredient.name,
                    "original_ingredient_name": original_ingredient_name,  # 添加原始食材名称
                    "ingredient_id": ingredient.id,
                    "recipe_ingredient_id": recipe_ingredient.id,  # 添加recipe_ingredient的ID
                    "quantity": str(quantity),
                    "unit_price": float(unit_price) if unit_price else 0.0,
                    "cost": 0.0,
                    "fallback_chain": fallback_chain  # 回退链信息（如果有）
                })

    return {
        "total_cost": total_cost,
        "currency": "CNY",
        "cost_per_serving": total_cost / (recipe.servings or 1),
        "cost_breakdown": cost_breakdown
    }


def calculate_recipe_cost_trend(
    recipe_id: int,
    user_id: int,
    db: Session,
    days: int = 90
) -> List[Dict]:
    """
    计算菜谱的成本趋势

    遍历指定日期范围，对于每一天，计算菜谱在该日期的成本。
    使用该日期之前的价格记录计算成本（向前查找）。

    Args:
        recipe_id: 菜谱ID
        user_id: 用户ID
        db: 数据库会话
        days: 查询天数（默认90天）

    Returns:
        成本趋势数据列表，每条记录包含：
        - date: 日期 (YYYY-MM-DD)
        - recorded_at: Unix 时间戳（秒）
        - total_cost: 总成本（分）
        - avg_cost: 平均成本（元）
    """
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        return []

    # 获取菜谱中的所有食材
    recipe_ingredients = db.query(RecipeIngredient).filter(
        RecipeIngredient.recipe_id == recipe_id,
        RecipeIngredient.is_optional != True  # 排除可选食材
    ).all()

    if not recipe_ingredients:
        return []

    # 获取最早的价格记录日期
    earliest_record = db.query(ProductRecord).filter(
        ProductRecord.user_id == user_id
    ).order_by(ProductRecord.recorded_at.asc()).first()

    if not earliest_record:
        return []

    # 确定日期范围
    end_date = datetime.now().date()
    start_date = max(earliest_record.recorded_at.date(), end_date - timedelta(days=days))

    # 生成日期列表
    date_list = []
    current_date = start_date
    while current_date <= end_date:
        date_list.append(current_date)
        current_date += timedelta(days=1)

    # 计算每一天的成本
    cost_trend = []
    for date in date_list:
        # 计算该日期 23:59:59 的成本（使用截至当天的最新价格）
        as_of_datetime = datetime.combine(date, datetime.max.time()) - timedelta(seconds=1)

        # 调用成本计算函数（不是 async）
        cost_result = calculate_recipe_cost_as_of(
            recipe_id, user_id, as_of_datetime, db
        )

        if cost_result and cost_result["total_cost"]:
            total_cost = cost_result["total_cost"]

            # 转换为分（整数存储）
            total_cost_cents = int(total_cost * 100)

            # 转换为 Unix 时间戳（使用当天 12:00）
            recorded_at_dt = datetime.combine(date, datetime.min.time()) + timedelta(hours=12)
            recorded_at = int(recorded_at_dt.timestamp())

            cost_trend.append({
                "date": date.strftime("%Y-%m-%d"),
                "recorded_at": recorded_at,
                "total_cost": total_cost_cents,
                "avg_cost": float(total_cost)
            })

    return cost_trend