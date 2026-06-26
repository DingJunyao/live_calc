"""数据导出序列化器：类型转换 + 各表 to_export_dict 纯函数。

约定：
- HowToCook 兼容字段保持原命名/结构；额外 id 与 xxx_id 为扩展字段。
- 所有外键冗余一个 _name 字段，便于人眼阅读与导入容错。
- Decimal→float，datetime→ISO 字符串，None 保持 None。
"""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional


def to_float(value: Any) -> Optional[float]:
    """Decimal/数字字符串→float；无法解析或 None→None。"""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (ValueError, InvalidOperation):
        return None


def to_iso(value: Any) -> Optional[str]:
    """datetime→ISO 8601 字符串；None→None。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return None


def convert_image_path(path: Optional[str]) -> Optional[str]:
    """数据库内的 /static/images/... 相对路径 → zip 内 images/... 路径。

    外链 http(s):// 原样返回（由调用方决定是否打包）。
    """
    if not path:
        return None
    if path.startswith("/static/"):
        return path[len("/static/"):]
    return path


def serialize_unit(unit: Any) -> dict:
    """Unit → units.json 元素。HowToCook: {name, aliases}；扩展: id 等。"""
    return {
        # HowToCook 兼容
        "name": unit.name,
        "aliases": [],  # 数据库无别名列；缩写见 abbreviation
        # 扩展
        "id": unit.id,
        "abbreviation": unit.abbreviation,
        "unit_type": unit.unit_type,
        "si_factor": to_float(unit.si_factor),
        "unit_system": unit.unit_system,
        "is_si_base": bool(unit.is_si_base),
        "is_common": bool(unit.is_common),
        "display_order": unit.display_order,
        "default_estimate": to_float(unit.default_estimate),
    }


def serialize_ingredient(
    ingredient: Any,
    category_display_name: Optional[str],
    usda_id: Any,
) -> dict:
    """Ingredient → ingredients.json 的 value 部分。

    HowToCook: {name, aliases, category, usda_id, usda_match_status}；扩展: id 等。
    usda_id 由调用方从关联 NutritionData 取。
    """
    has_usda = usda_id is not None and usda_id != ""
    return {
        # HowToCook 兼容
        "name": ingredient.name,
        "aliases": ingredient.aliases or [],
        "category": category_display_name,
        "usda_id": usda_id,
        "usda_match_status": "matched" if has_usda else "unmatched",
        # 扩展
        "id": ingredient.id,
        "category_id": ingredient.category_id,
        "density": to_float(ingredient.density),
        "default_unit_id": ingredient.default_unit_id,
        "piece_weight": to_float(ingredient.piece_weight),
        "piece_weight_unit_id": ingredient.piece_weight_unit_id,
        "serving_weight": to_float(ingredient.serving_weight),
        "serving_weight_unit_id": ingredient.serving_weight_unit_id,
        "nutrition_id": ingredient.nutrition_id,
        "is_imported": bool(ingredient.is_imported),
        "is_merged": bool(ingredient.is_merged),
        "merged_into_id": ingredient.merged_into_id,
    }


# 营养素 key → (中文名, 英文名) 映射；覆盖主要营养素。
# 未命中的 key 退化为 (key, key)，保证不丢数据。
NUTRIENT_KEY_NAME_MAP: dict[str, tuple[str, str]] = {
    "energy": ("能量", "Energy"),
    "protein": ("蛋白质", "Protein"),
    "fat": ("脂肪", "Total lipid (fat)"),
    "carbohydrate": ("碳水化合物", "Carbohydrate, by difference"),
    "fiber": ("膳食纤维", "Fiber, total dietary"),
    "sugars": ("糖", "Sugars, total"),
    "saturated_fat": ("饱和脂肪", "Fatty acids, total saturated"),
    "sodium": ("钠", "Sodium, Na"),
    "cholesterol": ("胆固醇", "Cholesterol"),
    "calcium": ("钙", "Calcium, Ca"),
    "iron": ("铁", "Iron, Fe"),
    "zinc": ("锌", "Zinc, Zn"),
    "selenium": ("硒", "Selenium, Se"),
    "vitamin_a": ("维生素A", "Vitamin A, RAE"),
    "vitamin_d": ("维生素D", "Vitamin D (D2 + D3)"),
    "vitamin_e": ("维生素E", "Vitamin E (alpha-tocopherol)"),
    "vitamin_c": ("维生素C", "Vitamin C, total ascorbic acid"),
    "thiamin": ("维生素B1（硫胺素）", "Thiamin"),
    "riboflavin": ("维生素B2（核黄素）", "Riboflavin"),
    "niacin": ("烟酸", "Niacin"),
    "vitamin_b6": ("维生素B6", "Vitamin B-6"),
    "vitamin_b12": ("维生素B12", "Vitamin B-12"),
    "folate": ("叶酸", "Folate, total"),
    "pantothenic_acid": ("泛酸", "Pantothenic acid"),
    "biotin": ("生物素", "Biotin"),
    "vitamin_k": ("维生素K", "Vitamin K (phylloquinone)"),
    "potassium": ("钾", "Potassium, K"),
    "magnesium": ("镁", "Magnesium, Mg"),
    "phosphorus": ("磷", "Phosphorus, P"),
}


def _flatten_nutrients(nutrients_json: Any) -> list[dict]:
    """嵌套 nutrients JSON → HowToCook 扁平数组 [{name, name_en, value, unit, nrp_pct, standard}]。"""
    if not isinstance(nutrients_json, dict):
        return []
    source_map = nutrients_json.get("all_nutrients") or nutrients_json.get("nutrient_details") or {}
    out = []
    for key, payload in source_map.items():
        if not isinstance(payload, dict):
            continue
        cn, en = NUTRIENT_KEY_NAME_MAP.get(key, (key, key))
        out.append({
            "name": cn,
            "name_en": en,
            "value": to_float(payload.get("value")),
            "unit": payload.get("unit"),
            "nrp_pct": to_float(payload.get("nrp_pct")),
            "standard": payload.get("standard"),
        })
    return out


def serialize_nutrition(nutrition_data: Any, ingredient_name: str) -> dict:
    """NutritionData → nutritions.json 元素。

    HowToCook: {usda_id, ingredient_name, usda_name, nutrients[]}；扩展: id + raw_nutrients。
    """
    return {
        # HowToCook 兼容
        "usda_id": nutrition_data.usda_id,
        "ingredient_name": ingredient_name,
        "usda_name": nutrition_data.usda_name,
        "nutrients": _flatten_nutrients(nutrition_data.nutrients),
        # 扩展
        "id": nutrition_data.id,
        "ingredient_id": nutrition_data.ingredient_id,
        "source": nutrition_data.source,
        "reference_amount": to_float(nutrition_data.reference_amount),
        "reference_unit": nutrition_data.reference_unit,
        "match_confidence": to_float(nutrition_data.match_confidence),
        "raw_nutrients": nutrition_data.nutrients,  # 原始嵌套，恢复导入用
    }


def _serialize_recipe_ingredient(
    ri: Any,
    ingredient_map: dict,
    unit_map: dict,
) -> dict:
    """RecipeIngredient → 菜谱 ingredients[] 元素（HowToCook + id）。"""
    ing_name = ingredient_map.get(ri.ingredient_id)
    unit_name = unit_map.get(ri.unit_id) if ri.unit_id is not None else None
    quantity = to_float(ri.quantity)
    # quantity 无法解析为数字时，退化为 quantity_description
    qty_desc = ""
    if quantity is None and ri.quantity:
        qty_desc = str(ri.quantity)
    return {
        # HowToCook 兼容
        "ingredient_name": ing_name,
        "quantity": quantity,
        "unit": unit_name,
        "original_quantity": ri.original_quantity,
        "quantity_range": ri.quantity_range,
        "is_optional": bool(ri.is_optional),
        "is_approximate": False,   # 数据库无，默认
        "is_estimated": False,     # 数据库无，默认
        "note": ri.note or "",
        "quantity_description": qty_desc,
        # 扩展
        "ingredient_id": ri.ingredient_id,
        "unit_id": ri.unit_id,
    }


def serialize_recipe(
    recipe: Any,
    recipe_ingredients: list,
    ingredient_map: dict,
    unit_map: dict,
) -> dict:
    """Recipe → recipes/{name}.json。

    HowToCook 字段保持兼容；扩展 id / result_ingredient_id 等。
    ingredient_map: {ingredient_id: name}；unit_map: {unit_id: name}。
    """
    return {
        # HowToCook 兼容
        "name": recipe.name,
        "source_file": recipe.source,            # ← Recipe.source
        "category": recipe.category,
        "difficulty": recipe.difficulty,
        "total_time_minutes": recipe.total_time_minutes,
        "servings": recipe.servings,
        "original_servings": None,               # 数据库无此字段
        "images": [convert_image_path(p) for p in (recipe.images or [])],
        "ingredients": [
            _serialize_recipe_ingredient(ri, ingredient_map, unit_map)
            for ri in recipe_ingredients
        ],
        "steps": recipe.cooking_steps or [],
        "tips": recipe.tips or [],
        "description": recipe.description or "",
        # 扩展
        "id": recipe.id,
        "tags": recipe.tags,
        "result_ingredient_id": recipe.result_ingredient_id,
    }


def serialize_unit_conversion(uc: Any, from_unit_name: Optional[str], to_unit_name: Optional[str]) -> dict:
    """UnitConversion → unit_conversions.json 元素。

    from_unit_name/to_unit_name 由调用方按 unit_id 解析冗余注入。
    """
    return {
        "id": uc.id,
        "from_unit_id": uc.from_unit_id,
        "from_unit_name": from_unit_name,
        "to_unit_id": uc.to_unit_id,
        "to_unit_name": to_unit_name,
        "conversion_factor": to_float(uc.conversion_factor),
        "formula": uc.formula,
        "is_bidirectional": bool(uc.is_bidirectional),
        "precision": uc.precision,
    }


def serialize_category(cat: Any) -> dict:
    """IngredientCategory → categories.json 元素。"""
    return {
        "id": cat.id,
        "name": cat.name,
        "display_name": cat.display_name,
        "parent_category_id": cat.parent_category_id,
        "sort_order": cat.sort_order,
        "description": cat.description,
    }


def serialize_hierarchy(h: Any, parent_name: Optional[str], child_name: Optional[str]) -> dict:
    """IngredientHierarchy → hierarchies.json 元素。

    parent_name/child_name 由调用方按 id 解析冗余注入。
    """
    return {
        "id": h.id,
        "parent_id": h.parent_id,
        "parent_name": parent_name,
        "child_id": h.child_id,
        "child_name": child_name,
        "relation_type": h.relation_type,
        "strength": h.strength,
    }


def serialize_entity_density(ed: Any, entity_name: Optional[str]) -> dict:
    """EntityDensity → entity_densities.json 元素。

    entity_name 由调用方按 entity_type+entity_id 解析冗余注入。
    """
    return {
        "id": ed.id,
        "entity_type": ed.entity_type,
        "entity_id": ed.entity_id,
        "entity_name": entity_name,
        "density": to_float(ed.density),
        "temperature": to_float(ed.temperature),
        "condition": ed.condition,
        "source": ed.source,
        "confidence": to_float(ed.confidence),
    }


def serialize_product(p: Any, ingredient_name: Optional[str], primary_barcode: Optional[str]) -> dict:
    """Product → products/{name}.json。

    primary_barcode 由调用方从 ProductBarcode 解析注入；image_url 走静态路径转换。
    """
    return {
        "id": p.id,
        "name": p.name,
        "brand": p.brand,
        "barcode": primary_barcode,
        "image_url": convert_image_path(p.image_url),
        "ingredient_id": p.ingredient_id,
        "ingredient_name": ingredient_name,
        "tags": p.tags,
        "aliases": p.aliases or [],
        "custom_nutrition_data": p.custom_nutrition_data,
        "custom_nutrition_source": p.custom_nutrition_source,
    }


def serialize_barcode(b: Any, product_name: Optional[str]) -> dict:
    """ProductBarcode → barcodes.json 元素。

    product_name 由调用方按 product_id 解析冗余注入。
    """
    return {
        "id": b.id,
        "product_id": b.product_id,
        "product_name": product_name,
        "barcode": b.barcode,
        "barcode_type": b.barcode_type,
        "is_primary": bool(b.is_primary),
        "is_active": bool(b.is_active),
    }


def serialize_product_link(link: Any, product_name: Optional[str], ingredient_name: Optional[str]) -> dict:
    """ProductIngredientLink → product_links.json 元素。

    product_name/ingredient_name 由调用方按 id 解析冗余注入。
    """
    return {
        "id": link.id,
        "product_id": link.product_id,
        "product_name": product_name,
        "ingredient_id": link.ingredient_id,
        "ingredient_name": ingredient_name,
    }


def serialize_price_record(
    pr: Any,
    product_name: Optional[str],
    merchant_name: Optional[str],
    original_unit_name: Optional[str],
    standard_unit_name: Optional[str],
) -> dict:
    """ProductRecord → price_records.json 元素。

    商品/商家/单位 name 由调用方按 id 解析冗余注入，便于人眼阅读与导入容错。
    Decimal→float，datetime→ISO 字符串。
    """
    return {
        "id": pr.id,
        "user_id": pr.user_id,
        "product_id": pr.product_id,
        "product_name": product_name,
        "merchant_id": pr.merchant_id,
        "merchant_name": merchant_name,
        "price": to_float(pr.price),
        "currency": pr.currency,
        "original_quantity": to_float(pr.original_quantity),
        "original_unit_id": pr.original_unit_id,
        "original_unit_name": original_unit_name,
        "standard_quantity": to_float(pr.standard_quantity),
        "standard_unit_id": pr.standard_unit_id,
        "standard_unit_name": standard_unit_name,
        "record_type": pr.record_type,
        "exchange_rate": to_float(pr.exchange_rate),
        "recorded_at": to_iso(pr.recorded_at),
        "notes": pr.notes,
    }


def serialize_merchant(m: Any) -> dict:
    """Location（商家）→ merchants.json 元素。

    与商品/价格记录解耦，独立导出商家基础信息。
    """
    return {
        "id": m.id,
        "name": m.name,
        "address": m.address,
        "latitude": to_float(m.latitude),
        "longitude": to_float(m.longitude),
        "is_open": bool(m.is_open),
    }


def serialize_entity_unit_override(
    euo: Any,
    entity_name: Optional[str],
    base_unit_name: Optional[str],
    weight_unit_name: Optional[str],
) -> dict:
    """EntityUnitOverride → entity_unit_overrides.json 元素。

    entity_name/base_unit_name/weight_unit_name 由调用方按 id 解析冗余注入。
    """
    return {
        "id": euo.id,
        "entity_type": euo.entity_type,
        "entity_id": euo.entity_id,
        "entity_name": entity_name,
        "unit_name": euo.unit_name,
        "base_unit_id": euo.base_unit_id,
        "base_unit_name": base_unit_name,
        "conversion_factor": to_float(euo.conversion_factor),
        "weight_per_unit": to_float(euo.weight_per_unit),
        "weight_unit_id": euo.weight_unit_id,
        "weight_unit_name": weight_unit_name,
        "is_default": bool(euo.is_default),
        "source": euo.source,
        "created_at": to_iso(euo.created_at),
        "updated_at": to_iso(euo.updated_at),
    }


def serialize_blacklist_group(group: Any, ingredients: list[dict]) -> dict:
    """BlacklistGroup → blacklist_groups.json 元素。
    ingredients: [{"ingredient_id": int, "ingredient_name": str, "is_ai_matched": bool}, ...]
    """
    return {
        "id": group.id,
        "name": group.name,
        "display_order": group.display_order,
        "is_active": bool(group.is_active),
        "ingredients": ingredients,
    }


def serialize_blacklist_entry(entry: Any, ingredient_name: Optional[str]) -> dict:
    """UserIngredientBlacklist → user_ingredient_blacklist.json 元素。"""
    return {
        "id": entry.id,
        "ingredient_id": entry.ingredient_id,
        "ingredient_name": ingredient_name,
        "reason": entry.reason,
        "source": entry.source,
        "blacklist_group_id": entry.blacklist_group_id,
        "created_at": to_iso(entry.created_at),
    }


def serialize_blacklist_subscription(sub: Any, group_name: Optional[str]) -> dict:
    """BlacklistGroupSubscription → blacklist_group_subscriptions.json 元素。"""
    return {
        "id": sub.id,
        "blacklist_group_id": sub.blacklist_group_id,
        "blacklist_group_name": group_name,
        "created_at": to_iso(sub.created_at),
    }


def serialize_user_place(up: Any) -> dict:
    """UserPlace → user_places.json 元素。用户常用地点（家/公司等）。"""
    return {
        "id": up.id,
        "name": up.name,
        "kind": up.kind,
        "latitude": to_float(up.latitude),
        "longitude": to_float(up.longitude),
        "address": up.address,
        "is_default": bool(up.is_default),
        "sort_order": up.sort_order,
    }
