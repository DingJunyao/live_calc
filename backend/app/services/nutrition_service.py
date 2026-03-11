from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from app.models.nutrition import Ingredient, IngredientNutritionMapping  # 其他模型从 nutrition 导入
from app.models.nutrition_data import NutritionData  # NutritionData 从 nutrition_data 导入，避免冲突
from decimal import Decimal
import json


async def search_nutrition(
    query: str,
    fuzzy: bool = False,
    limit: int = 10,
    db: Session = None
) -> List[Dict]:
    """搜索营养数据"""
    results = []

    # 精确匹配
    exact_matches = db.query(NutritionData).filter(
        (NutritionData.name_zh == query) | (NutritionData.name_en.ilike(f"%{query}%"))
    ).limit(limit).all()

    for match in exact_matches:
        results.append({
            "nutrition_id": match.id,
            "name_en": match.name_en,
            "name_zh": match.name_zh,
            "confidence": Decimal("1.00")
        })

    # 模糊匹配
    if fuzzy and len(results) < limit:
        fuzzy_matches = db.query(NutritionData).filter(
            NutritionData.name_zh.contains(query)
        ).limit(limit - len(results)).all()

        for match in fuzzy_matches:
            if match.id not in [r["nutrition_id"] for r in results]:
                results.append({
                    "nutrition_id": match.id,
                    "name_en": match.name_en,
                    "name_zh": match.name_zh,
                    "confidence": Decimal("0.70")
                })

    return results[:limit]


async def match_ingredient(
    ingredient_name: str,
    db: Session = None
) -> List[Dict]:
    """匹配食材到营养数据（混合推荐算法）"""

    matches = []

    # 1. 优先查找映射表精确匹配
    ingredient = db.query(Ingredient).filter(
        Ingredient.name == ingredient_name
    ).first()

    if ingredient and ingredient.aliases:
        for alias_name in ingredient.aliases:
            matches.extend(await search_nutrition(alias_name, db=db))

    # 2. 未匹配则关键词模糊搜索
    if not matches:
        keywords = _extract_keywords(ingredient_name)
        for keyword in keywords:
            matches.extend(await search_nutrition(keyword, fuzzy=True, db=db))

    # 3. 去重并排序
    unique_matches = {}
    for match in matches:
        key = match["nutrition_id"]
        if key not in unique_matches:
            unique_matches[key] = match
        else:
            if match["confidence"] > unique_matches[key]["confidence"]:
                unique_matches[key] = match

    # 按置信度排序
    sorted_matches = sorted(
        unique_matches.values(),
        key=lambda x: x["confidence"],
        reverse=True
    )

    return sorted_matches[:5]


def _extract_keywords(text: str) -> List[str]:
    """提取关键词"""
    stopwords = ["有机", "新鲜", "进口", "特级", "精选", "个大", ""]

    keywords = [text]
    for word in stopwords:
        if word in text:
            keywords.append(text.replace(word, ""))

    return list(set([k for k in keywords if k]))


async def correct_mapping(
    ingredient_name: str,
    nutrition_id: int,
    db: Session = None
) -> bool:
    """更正映射并学习"""
    # 查找或创建食材
    ingredient = db.query(Ingredient).filter(
        Ingredient.name == ingredient_name
    ).first()

    if not ingredient:
        nutrition = db.query(NutritionData).filter(
            NutritionData.id == nutrition_id
        ).first()
        if not nutrition:
            return False

        ingredient = Ingredient(
            name=ingredient_name,
            nutrition_id=nutrition_id,
            aliases=[ingredient_name]
        )
        db.add(ingredient)
        db.flush()

    else:
        nutrition = db.query(NutritionData).filter(
            NutritionData.id == nutrition_id
        ).first()
        if not nutrition:
            return False

        # 更新映射
        ingredient.nutrition_id = nutrition_id
        # 更新别名
        aliases = ingredient.aliases or []
        if ingredient_name not in aliases:
            aliases = list(aliases) + [ingredient_name]
            ingredient.aliases = aliases
        db.flush()

    # 创建或更新映射
    mapping = db.query(IngredientNutritionMapping).filter(
        IngredientNutritionMapping.ingredient_id == ingredient.id,
        IngredientNutritionMapping.nutrition_id == nutrition_id
    ).first()

    if mapping:
        mapping.confidence = Decimal("1.00")
        mapping.priority += 1
    else:
        mapping = IngredientNutritionMapping(
            ingredient_id=ingredient.id,
            nutrition_id=nutrition_id,
            priority=1,
            confidence=Decimal("1.00")
        )
        db.add(mapping)

    db.commit()
    return True