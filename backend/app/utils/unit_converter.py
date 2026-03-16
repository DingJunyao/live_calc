from decimal import Decimal
from typing import Tuple

# 重量单位转换（转换为克）
WEIGHT_CONVERSION = {
    "g": (1, "g"),
    "kg": (1000, "g"),
    "斤": (500, "g"),
    "两": (50, "g"),
    "lb": (453.592, "g"),
    "oz": (28.3495, "g"),
}

# 容量单位转换（转换为毫升）
VOLUME_CONVERSION = {
    "ml": (1, "ml"),
    "mL": (1, "ml"),
    "l": (1000, "ml"),
    "杯": (240, "ml"),
    "汤匙": (15, "ml"),
    "茶匙": (5, "ml"),
}


def convert_to_standard(quantity: Decimal, unit: str) -> Tuple[Decimal, str]:
    """转换为标准单位

    将单位转换为标准单位（重量为 g，体积为 ml）
    注意：重量和体积之间的转换需要密度信息，此函数不处理此类转换
    """
    unit_lower = unit.lower()

    # 尝试重量单位
    if unit_lower in WEIGHT_CONVERSION:
        factor, standard_unit = WEIGHT_CONVERSION[unit_lower]
        return Decimal(str(quantity)) * Decimal(str(factor)), standard_unit

    # 尝试容量单位
    if unit_lower in VOLUME_CONVERSION or unit in VOLUME_CONVERSION:
        # 支持大小写混合匹配
        factor, standard_unit = VOLUME_CONVERSION.get(unit_lower) or VOLUME_CONVERSION.get(unit)
        return Decimal(str(quantity)) * Decimal(str(factor)), standard_unit

    # 其他单位不转换
    return quantity, unit
