"""USDA FoodData Central JSON 解析与去重。"""
from typing import Any

from app.services.usda.nutrient_mapping import map_nutrient_name

# data_type 优先级：foundation > sr_legacy（数字越小越优）
_TYPE_PRIORITY = {"foundation": 0, "sr_legacy": 1}


def parse_usda_food(raw: dict, data_type: str) -> dict:
    """把一条 USDA raw 食材解析为内部 dict（含 nutrients 子表）。

    支持两种结构：

    - 新版（``foodNutrients`` 中每项含 ``nutrient`` 子对象，含 ``name``/``number``）
    - 旧版/简化（``foodComponents`` 或扁平 ``nutrient``）
    """
    nutrients = []
    food_nutrients = raw.get("foodNutrients") or raw.get("foodComponents") or []
    for fn in food_nutrients:
        if not isinstance(fn, dict):
            continue
        # nutrient 可能为 None（USDA 数据中 fn["nutrient"]=null），回退到 fn 本身
        nutrient = fn.get("nutrient") or fn
        if not isinstance(nutrient, dict):
            continue
        name = nutrient.get("name")
        if not name:
            continue  # 无名称的营养素无意义，跳过
        nutrient_no = nutrient.get("number")
        nutrients.append(
            {
                "nutrient_no": str(nutrient_no) if nutrient_no else None,
                "name": name,
                "name_zh": map_nutrient_name(name),
                "amount": float(fn.get("amount", 0) or 0),
                "unit_name": fn.get("unitName") or nutrient.get("unitName") or "",
            }
        )
    return {
        "fdc_id": raw.get("fdcId"),
        "data_type": data_type,
        "description": raw.get("description", "").strip(),
        "publication_date": raw.get("publicationDate"),
        "nutrients": nutrients,
    }


def _food_sort_key(food: dict) -> tuple:
    """去重排序键：优先级小者胜，其次营养素多者胜。"""
    return (
        _TYPE_PRIORITY.get(food["data_type"], 99),
        -len(food.get("nutrients", [])),
    )


def dedupe_foods(foods: list[dict]) -> list[dict]:
    """同 description 只留最优一条（foundation 优先，其次营养素更多）。"""
    best: dict[str, dict] = {}
    for food in foods:
        desc = food["description"]
        if not desc:
            continue
        if desc not in best or _food_sort_key(food) < _food_sort_key(best[desc]):
            best[desc] = food
    return list(best.values())
