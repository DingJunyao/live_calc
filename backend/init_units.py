"""
初始化单位数据的脚本
包含常见的国际单位和中国地区常用的单位
"""

from app.core.database import SessionLocal
from app.models.unit import Unit, UnitConversion
from app.models.region_unit_setting import RegionUnitSetting
from app.models.ingredient_category import IngredientCategory

def init_units():
    db = SessionLocal()

    try:
        # 添加国际单位制基本单位
        si_units = [
            {"name": "meter", "abbreviation": "m", "unit_type": "length", "is_si_base": True},
            {"name": "kilogram", "abbreviation": "kg", "unit_type": "mass", "is_si_base": True},
            {"name": "gram", "abbreviation": "g", "unit_type": "mass", "si_factor": 0.001},
            {"name": "liter", "abbreviation": "L", "unit_type": "volume", "is_si_base": True},
            {"name": "milliliter", "abbreviation": "mL", "unit_type": "volume", "si_factor": 0.001},
            {"name": "second", "abbreviation": "s", "unit_type": "time", "is_si_base": True},
        ]

        for unit_data in si_units:
            existing = db.query(Unit).filter(Unit.abbreviation == unit_data["abbreviation"]).first()
            if not existing:
                unit = Unit(**unit_data)
                db.add(unit)

        # 添加常用单位
        common_units = [
            # 质量单位
            {"name": "jin", "abbreviation": "jin", "unit_type": "mass", "si_factor": 0.5, "is_common": True},
            {"name": "liang", "abbreviation": "liang", "unit_type": "mass", "si_factor": 0.05, "is_common": True},
            {"name": "pound", "abbreviation": "lb", "unit_type": "mass", "si_factor": 0.453592, "is_common": True},
            {"name": "ounce", "abbreviation": "oz", "unit_type": "mass", "si_factor": 0.0283495, "is_common": True},

            # 体积单位
            {"name": "cup", "abbreviation": "cup", "unit_type": "volume", "si_factor": 0.24, "is_common": True},
            {"name": "tablespoon", "abbreviation": "tbsp", "unit_type": "volume", "si_factor": 0.015, "is_common": True},
            {"name": "teaspoon", "abbreviation": "tsp", "unit_type": "volume", "si_factor": 0.005, "is_common": True},
            {"name": "fluid ounce", "abbreviation": "fl oz", "unit_type": "volume", "si_factor": 0.03, "is_common": True},

            # 长度单位
            {"name": "centimeter", "abbreviation": "cm", "unit_type": "length", "si_factor": 0.01, "is_common": True},
            {"name": "millimeter", "abbreviation": "mm", "unit_type": "length", "si_factor": 0.001, "is_common": True},
            {"name": "inch", "abbreviation": "in", "unit_type": "length", "si_factor": 0.0254, "is_common": True},
        ]

        for unit_data in common_units:
            existing = db.query(Unit).filter(Unit.abbreviation == unit_data["abbreviation"]).first()
            if not existing:
                unit = Unit(**unit_data)
                db.add(unit)

        db.commit()

        # 添加单位转换关系
        unit_conversions = [
            # 质量转换
            {"from_unit": "kg", "to_unit": "g", "factor": 1000.0},
            {"from_unit": "g", "to_unit": "kg", "factor": 0.001},
            {"from_unit": "jin", "to_unit": "g", "factor": 500.0},
            {"from_unit": "g", "to_unit": "jin", "factor": 0.002},
            {"from_unit": "jin", "to_unit": "kg", "factor": 0.5},
            {"from_unit": "kg", "to_unit": "jin", "factor": 2.0},
            {"from_unit": "liang", "to_unit": "g", "factor": 50.0},
            {"from_unit": "g", "to_unit": "liang", "factor": 0.02},
            {"from_unit": "lb", "to_unit": "kg", "factor": 0.453592},
            {"from_unit": "kg", "to_unit": "lb", "factor": 2.20462},
            {"from_unit": "oz", "to_unit": "g", "factor": 28.3495},
            {"from_unit": "g", "to_unit": "oz", "factor": 0.035274},

            # 体积转换
            {"from_unit": "L", "to_unit": "mL", "factor": 1000.0},
            {"from_unit": "mL", "to_unit": "L", "factor": 0.001},
            {"from_unit": "cup", "to_unit": "mL", "factor": 240.0},
            {"from_unit": "mL", "to_unit": "cup", "factor": 0.00416667},
            {"from_unit": "tbsp", "to_unit": "mL", "factor": 15.0},
            {"from_unit": "mL", "to_unit": "tbsp", "factor": 0.0666667},
            {"from_unit": "tsp", "to_unit": "mL", "factor": 5.0},
            {"from_unit": "mL", "to_unit": "tsp", "factor": 0.2},
            {"from_unit": "fl oz", "to_unit": "mL", "factor": 30.0},
            {"from_unit": "mL", "to_unit": "fl oz", "factor": 0.0333333},

            # 长度转换
            {"from_unit": "m", "to_unit": "cm", "factor": 100.0},
            {"from_unit": "cm", "to_unit": "m", "factor": 0.01},
            {"from_unit": "cm", "to_unit": "mm", "factor": 10.0},
            {"from_unit": "mm", "to_unit": "cm", "factor": 0.1},
            {"from_unit": "in", "to_unit": "cm", "factor": 2.54},
            {"from_unit": "cm", "to_unit": "in", "factor": 0.393701},
        ]

        for conv_data in unit_conversions:
            from_unit = db.query(Unit).filter(Unit.abbreviation == conv_data["from_unit"]).first()
            to_unit = db.query(Unit).filter(Unit.abbreviation == conv_data["to_unit"]).first()

            if from_unit and to_unit:
                existing = db.query(UnitConversion).filter(
                    UnitConversion.from_unit_id == from_unit.id,
                    UnitConversion.to_unit_id == to_unit.id
                ).first()

                if not existing:
                    conversion = UnitConversion(
                        from_unit_id=from_unit.id,
                        to_unit_id=to_unit.id,
                        conversion_factor=conv_data["factor"],
                        precision=6
                    )
                    db.add(conversion)

        db.commit()

        # 添加中国地区单位设置
        cn_region = db.query(RegionUnitSetting).filter(RegionUnitSetting.region_code == "CN").first()
        if not cn_region:
            # 获取常用单位ID
            jin_unit = db.query(Unit).filter(Unit.abbreviation == "jin").first()
            g_unit = db.query(Unit).filter(Unit.abbreviation == "g").first()
            ml_unit = db.query(Unit).filter(Unit.abbreviation == "mL").first()

            region_setting = RegionUnitSetting(
                region_code="CN",
                region_name="中国",
                default_mass_unit=jin_unit.id if jin_unit else g_unit.id,
                default_volume_unit=ml_unit.id if ml_unit else None
            )
            db.add(region_setting)
            db.commit()

        # 添加一些基本食材类别
        categories = [
            {"name": "grains", "display_name": "谷物", "description": "各类谷物、面粉等"},
            {"name": "vegetables", "display_name": "蔬菜", "description": "各类蔬菜"},
            {"name": "fruits", "display_name": "水果", "description": "各类水果"},
            {"name": "meat", "display_name": "肉类", "description": "各种肉类"},
            {"name": "seafood", "display_name": "海鲜", "description": "鱼类、虾类等"},
            {"name": "dairy", "display_name": "乳制品", "description": "牛奶、奶酪等"},
            {"name": "seasoning", "display_name": "调味品", "description": "盐、糖、香料等"}
        ]

        for cat_data in categories:
            existing = db.query(IngredientCategory).filter(IngredientCategory.name == cat_data["name"]).first()
            if not existing:
                category = IngredientCategory(**cat_data)
                db.add(category)

        db.commit()
        print("Units, conversions, and categories initialized successfully!")

    finally:
        db.close()


if __name__ == "__main__":
    init_units()