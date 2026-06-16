"""原料/商品 USDA 匹配写入。

原料（match_ingredient）：
    清空该原料现有 NutritionData → 用 USDA 营养素构造一条新 NutritionData
    （source = ``usda_manual_match``），结构与 nutrition_import_service 保持一致。

商品（match_product）：
    清空 ``Product.custom_nutrition_data`` → 复制所属原料 core_nutrients 的
    中文名集合作为「骨架」（值置 0）→ 再用 USDA 命中的营养素覆盖。
    最终写入 ``custom_nutrition_data`` 的结构与 ``NutritionData.nutrients``
    一致（三层 core_nutrients / all_nutrients / nutrient_details），
    因为前端 ProductDetail.vue 读取的正是
    ``custom_nutrition_data.all_nutrients``（参见该文件 startEditNutrition）。

注意：
    ``Product.ingredient_id`` 在模型中为 nullable=False，因此 match_product
    始终基于原料的 core_nutrients 构建骨架；若原料无营养数据，则骨架为空，
    仅写入 USDA 命中项。
"""
from __future__ import annotations

from app.models.nutrition import Ingredient
from app.models.nutrition_data import NutritionData
from app.models.product_entity import Product
from app.models.usda import UsdaFood, UsdaFoodNutrient
from app.services.usda.nutrient_mapping import map_nutrient_name
from fastapi import HTTPException
from sqlalchemy.orm import Session

# 核心营养素中文名集合（与 nutrition_import_service.CORE_DISPLAY_MAP 对齐）。
CORE_NAMES = {
    "能量", "蛋白质", "脂肪", "碳水化合物", "膳食纤维",
    "钙", "铁", "钠", "钾",
    "维生素A", "维生素C", "维生素B1", "维生素B2", "维生素B12",
    "维生素D", "维生素E", "维生素K",
    "饱和脂肪酸", "胆固醇", "叶酸",
}

# 核心营养素中文名 -> 英文 key（对齐 nutrition_import_service.CN_TO_KEY）。
NAME_ZH_TO_KEY = {
    "能量": "energy", "蛋白质": "protein", "脂肪": "fat",
    "碳水化合物": "carbohydrate", "膳食纤维": "fiber",
    "钙": "calcium", "铁": "iron", "钠": "sodium", "钾": "potassium",
    "维生素A": "vitamin_a_rae", "维生素C": "vitamin_c",
    "维生素B1": "vitamin_b1", "维生素B2": "vitamin_b2", "维生素B12": "vitamin_b12",
    "维生素D": "vitamin_d", "维生素E": "vitamin_e", "维生素K": "vitamin_k",
    "饱和脂肪酸": "saturated_fat", "胆固醇": "cholesterol", "叶酸": "folate",
}


def _resolve_zh(n: UsdaFoodNutrient) -> str:
    """取营养素中文名：优先 name_zh，否则查静态映射表，最后回退英文名。"""
    if n.name_zh:
        return n.name_zh
    mapped = map_nutrient_name(n.name)
    return mapped or n.name


def _derive_key(name_zh: str, nutrient_no: str | None) -> str:
    """核心营养素用预定义英文 key，其余回退 nutrient_no 或中文名。"""
    return NAME_ZH_TO_KEY.get(name_zh) or (nutrient_no or name_zh)


def _build_nutrition_json(usda_nutrients: list[UsdaFoodNutrient]) -> dict:
    """把 USDA 营养素行构造成三层结构，对齐 NutritionData.nutrients 格式。

    结构：
        {
          "core_nutrients": {zh_name: {value, unit, key}},
          "all_nutrients": {eng_key: {value, unit, key}},
          "nutrient_details": {eng_key: {value, unit, key}},
        }
    """
    core: dict[str, dict] = {}
    all_n: dict[str, dict] = {}
    details: dict[str, dict] = {}

    for n in usda_nutrients:
        zh = _resolve_zh(n)
        key = _derive_key(zh, n.nutrient_no)
        entry = {"value": n.amount, "unit": n.unit_name, "key": key}
        all_n[key] = dict(entry)
        details[key] = dict(entry)
        if zh in CORE_NAMES:
            core[zh] = dict(entry)

    return {
        "core_nutrients": core,
        "all_nutrients": all_n,
        "nutrient_details": details,
    }


def _get_food_or_404(db: Session, fdc_id: int) -> tuple[UsdaFood, list[UsdaFoodNutrient]]:
    food = db.query(UsdaFood).filter(UsdaFood.fdc_id == fdc_id).first()
    if not food:
        raise HTTPException(status_code=404, detail="USDA 食材不存在")
    nutrients = (
        db.query(UsdaFoodNutrient)
        .filter(UsdaFoodNutrient.fdc_id == fdc_id)
        .all()
    )
    return food, nutrients


def match_ingredient(db: Session, ingredient_id: int, fdc_id: int) -> dict:
    """把 USDA 食材的营养数据写入指定原料（覆盖该原料的所有 NutritionData）。"""
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="原料不存在")
    food, nutrients = _get_food_or_404(db, fdc_id)

    # 清空该原料现有 NutritionData
    db.query(NutritionData).filter(
        NutritionData.ingredient_id == ingredient_id
    ).delete(synchronize_session=False)

    nd = NutritionData(
        ingredient_id=ingredient_id,
        source="usda_manual_match",
        usda_id=str(fdc_id),
        usda_name=food.description,
        nutrients=_build_nutrition_json(nutrients),
        reference_amount=100.0,
        reference_unit="g",
    )
    db.add(nd)
    db.commit()
    return {"ingredient_id": ingredient_id, "fdc_id": fdc_id}


def match_product(db: Session, product_id: int, fdc_id: int) -> dict:
    """把 USDA 食材的营养数据写入商品 custom_nutrition_data。

    1. 先复制所属原料 core_nutrients 中文名集合作为「骨架」（值置 0），
       保留原料已有的营养素项（便于后续按原料营养回退对比）。
    2. 再用 USDA 命中的营养素覆盖（值取 USDA amount）。
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    food, nutrients = _get_food_or_404(db, fdc_id)

    # 收集骨架：原料 core_nutrients 的中文名 -> 值为 0 的占位项。
    skeleton: dict[str, dict] = {}
    if product.ingredient_id:
        ing_nd = (
            db.query(NutritionData)
            .filter(NutritionData.ingredient_id == product.ingredient_id)
            .order_by(NutritionData.id.desc())
            .first()
        )
        if ing_nd and ing_nd.nutrients:
            for name, entry in (ing_nd.nutrients.get("core_nutrients") or {}).items():
                if not isinstance(entry, dict):
                    continue
                key = entry.get("key") or _derive_key(name, None)
                placeholder = {"value": 0, "unit": entry.get("unit", "g"), "key": key}
                skeleton[name] = placeholder

    # 构建 USDA 营养素三层结构。
    usda_struct = _build_nutrition_json(nutrients)

    # 用骨架补齐 core_nutrients：USDA 未命中但原料有的项，保留为 0。
    merged_core = dict(skeleton)
    merged_core.update(usda_struct["core_nutrients"])

    # all_nutrients / nutrient_details 以 USDA 为准，
    # 但把骨架中 USDA 未覆盖的项也补进去（key 取骨架 key）。
    merged_all = dict(usda_struct["all_nutrients"])
    merged_details = dict(usda_struct["nutrient_details"])
    for name, ph in skeleton.items():
        k = ph.get("key") or name
        if k not in merged_all:
            merged_all[k] = dict(ph)
        if k not in merged_details:
            merged_details[k] = dict(ph)

    product.custom_nutrition_data = {
        "core_nutrients": merged_core,
        "all_nutrients": merged_all,
        "nutrient_details": merged_details,
        "source": "usda_manual_match",
        "usda_id": str(fdc_id),
        "usda_name": food.description,
        "reference_amount": 100.0,
        "reference_unit": "g",
    }
    db.commit()
    return {"product_id": product_id, "fdc_id": fdc_id}
