"""
营养功能测试脚本

测试营养数据导入、计算和查询功能
"""
import sys
import os

# 添加后端路径到 sys.path
sys.path.insert(0, '/home/ding/code/live_calc/backend')

from app.core.database import get_db
from app.services.nutrition_import_service import NutritionImportService
from app.services.nutrition_calculator import NutritionCalculator


def test_nutrition_import():
    """测试营养数据导入"""
    print("🧪 测试营养数据导入...")

    try:
        from app.core.database import SessionLocal
        db = SessionLocal()

        service = NutritionImportService(db)
        result = service.import_all(mode="incremental", force_update=False)

        print(f"✅ 导入完成！")
        print(f"   总计: {result['total']}")
        print(f"   新增: {result['imported']}")
        print(f"   更新: {result['updated']}")
        print(f"   跳过: {result['skipped']}")
        print(f"   失败: {result['failed']}")

        if result['errors']:
            print(f"\n⚠️ 错误信息:")
            for error in result['errors'][:5]:  # 只显示前5个错误
                print(f"   - {error}")

        db.close()
        return result

    except Exception as e:
        print(f"❌ 导入失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_nutrition_statistics():
    """测试营养数据统计"""
    print("\n🧪 测试营养数据统计...")

    try:
        from app.core.database import SessionLocal
        db = SessionLocal()

        service = NutritionImportService(db)
        stats = service.get_nutrient_statistics()

        print(f"✅ 统计信息:")
        print(f"   总食材数: {stats['total_ingredients']}")
        print(f"   有营养数据: {stats['ingredients_with_nutrition']}")
        print(f"   覆盖率: {stats['coverage_percentage']:.2f}%")

        print(f"\n   核心营养素覆盖率:")
        for nutrient, coverage in list(stats['nutrient_coverage'].items())[:5]:
            print(f"     {nutrient}: {coverage['count']} ({coverage['percentage']:.2f}%)")

        db.close()
        return stats

    except Exception as e:
        print(f"❌ 统计失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_nutrition_calculation():
    """测试营养数据计算"""
    print("\n🧪 测试营养数据计算...")

    try:
        from app.core.database import SessionLocal
        from app.models.nutrition import Ingredient
        db = SessionLocal()

        # 获取第一个有营养数据的食材
        from app.models.nutrition_data import NutritionData

        nutrition = db.query(NutritionData).first()
        if not nutrition:
            print("⚠️  没有找到营养数据，请先导入数据")
            db.close()
            return None

        ingredient = db.query(Ingredient).filter(Ingredient.id == nutrition.ingredient_id).first()
        if not ingredient:
            print("⚠️  没有找到对应的食材")
            db.close()
            return None

        calculator = NutritionCalculator(db)

        # 测试不同数量的营养计算
        for quantity in [100, 200, 50]:
            result = calculator.calculate_ingredient_nutrition(nutrition.ingredient_id, quantity, "g")
            if result:
                print(f"\n   {ingredient.name} ({quantity}g):")
                core_nutrients = result['nutrition'].get('core_nutrients', {})
                for name, data in list(core_nutrients.items())[:3]:
                    print(f"     {name}: {data['value']}{data['unit']} (NRV: {data['nrp_pct']}%)")

        db.close()
        return True

    except Exception as e:
        print(f"❌ 计算失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_recipe_nutrition():
    """测试菜谱营养计算"""
    print("\n🧪 测试菜谱营养计算...")

    try:
        from app.core.database import SessionLocal
        from app.models.recipe import Recipe
        db = SessionLocal()

        # 获取第一个菜谱
        recipe = db.query(Recipe).first()
        if not recipe:
            print("⚠️  没有找到菜谱数据")
            db.close()
            return None

        calculator = NutritionCalculator(db)
        result = calculator.calculate_recipe_nutrition(recipe.id)

        if result:
            print(f"✅ 菜谱营养计算完成:")
            print(f"   菜谱: {result['recipe_name']}")
            print(f"   份数: {result['servings']}")
            print(f"   原料数: {len(result['ingredient_details'])}")

            per_serving = result['per_serving_nutrition']
            core_nutrients = per_serving.get('core_nutrients', {})
            print(f"\n   每份营养（前5项）:")
            for name, data in list(core_nutrients.items())[:5]:
                print(f"     {name}: {data['value']}{data['unit']} (NRV: {data['nrp_pct']}%)")

        db.close()
        return result

    except Exception as e:
        print(f"❌ 菜谱计算失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主测试函数"""
    print("=" * 60)
    print("🧪 生活计算器 - 营养功能测试")
    print("=" * 60)

    # 测试导入
    import_result = test_nutrition_import()

    # 如果导入成功，测试其他功能
    if import_result and import_result.get('success'):
        # 测试统计
        test_nutrition_statistics()

        # 测试计算
        test_nutrition_calculation()

        # 测试菜谱计算
        test_recipe_nutrition()

    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
