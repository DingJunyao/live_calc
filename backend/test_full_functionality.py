"""
测试食材匹配和转换服务的脚本
"""

from app.core.database import SessionLocal
from app.services.unit_conversion_service import UnitConversionService
from app.services.ingredient_matcher import IngredientMatcher
from app.models.nutrition import Ingredient
from app.models.unit import Unit
from app.models.ingredient_density import IngredientDensity
from sqlalchemy import or_

def test_services():
    db = SessionLocal()

    try:
        # 测试单位转换服务
        print("Testing Unit Conversion Service...")
        unit_service = UnitConversionService(db)

        # 基本转换测试
        result = unit_service.convert(1, "kg", "g")
        print(f"1 kg = {result} g")

        result = unit_service.convert(500, "g", "kg")
        print(f"500 g = {result} kg")

        result = unit_service.convert(2, "jin", "g")
        print(f"2 jin = {result} g")

        result = unit_service.convert(1000, "g", "jin")
        print(f"1000 g = {result} jin")

        # 测试体积到重量转换
        print("\nTesting Volume to Weight Conversion...")

        # 查询数据库中的食材和单位信息
        water_ing = db.query(Ingredient).filter(or_(Ingredient.name == "water", Ingredient.name.like("%water%"))).first()
        if water_ing:
            print(f"Found ingredient: {water_ing.name}")

            # 查找水的密度信息
            density = db.query(IngredientDensity).filter(IngredientDensity.ingredient_id == water_ing.id).first()
            if density:
                print(f"Found density info for {water_ing.name}")

                volume_ml = 500  # 500 mL
                # 使用服务的转换方法
                result = unit_service.convert_volume_to_weight(volume_ml, "mL", water_ing.name)
                if result:
                    weight, unit_abbr = result
                    print(f"{volume_ml} mL {water_ing.name} = {weight} {unit_abbr}")
                else:
                    print(f"Could not convert {volume_ml} mL {water_ing.name}")
            else:
                print(f"No density info found for {water_ing.name}")
        else:
            print("No 'water' ingredient found in database")

        # 测试食材匹配服务
        print("\nTesting Ingredient Matcher...")
        matcher = IngredientMatcher(db)

        # 搜索一些食材
        matches = matcher.match_product_to_ingredient("flour")
        print(f"Matches for 'flour':")
        for ingredient, confidence in matches[:5]:  # 只显示前5个结果
            print(f"  - {ingredient.name}: {confidence:.2f}")

        # 测试层级关系解析
        specific_ingredient = matcher.resolve_ingredient_hierarchy("flour", "bread")
        if specific_ingredient:
            print(f"\nSpecific ingredient for 'flour' with grade 'bread': {specific_ingredient.name}")
        else:
            print(f"\nNo specific ingredient found for 'flour' with grade 'bread'")

        print("\nAll tests completed successfully!")

    finally:
        db.close()

if __name__ == "__main__":
    test_services()