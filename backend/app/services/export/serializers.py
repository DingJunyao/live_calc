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
