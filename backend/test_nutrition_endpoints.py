"""
测试营养 API 端点

验证原料和商品的营养数据查询功能
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_health_check():
    """测试后端健康检查"""
    print("🔍 测试后端健康检查...")
    try:
        response = requests.get(f"{BASE_URL}/auth/config")
        print(f"✅ 后端运行正常: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ 后端连接失败: {e}")
        return False

def test_ingredient_nutrition(ingredient_id: int = 1):
    """测试原料营养数据查询"""
    print(f"\n🔍 测试原料营养数据查询 (ID: {ingredient_id})...")
    try:
        response = requests.get(f"{BASE_URL}/nutrition/ingredients/{ingredient_id}/nutrition")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 原料营养数据获取成功:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return True
        else:
            print(f"❌ 原料营养数据获取失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 原料营养数据查询失败: {e}")
        return False

def test_product_nutrition(product_id: int = 1):
    """测试商品营养数据查询"""
    print(f"\n🔍 测试商品营养数据查询 (ID: {product_id})...")
    try:
        response = requests.get(f"{BASE_URL}/nutrition/products/{product_id}/nutrition")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 商品营养数据获取成功:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return True
        else:
            print(f"❌ 商品营养数据获取失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 商品营养数据查询失败: {e}")
        return False

def test_recipe_nutrition(recipe_id: int = 1):
    """测试菜谱营养数据计算"""
    print(f"\n🔍 测试菜谱营养数据计算 (ID: {recipe_id})...")
    try:
        response = requests.get(f"{BASE_URL}/nutrition/recipes/{recipe_id}/nutrition")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 菜谱营养数据计算成功:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return True
        else:
            print(f"❌ 菜谱营养数据计算失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 菜谱营养数据计算失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 50)
    print("🧪 营养 API 端点测试")
    print("=" * 50)

    # 健康检查
    if not test_health_check():
        print("\n⚠️  后端服务未运行，请先启动后端服务")
        return

    # 测试各项功能
    results = {
        "原料营养": test_ingredient_nutrition(),
        "商品营养": test_product_nutrition(),
        "菜谱营养": test_recipe_nutrition()
    }

    # 总结
    print("\n" + "=" * 50)
    print("📊 测试结果总结")
    print("=" * 50)
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")

    # 建议
    print("\n💡 建议:")
    print("1. 如果测试失败，请检查：")
    print("   - 后端服务是否正常运行")
    print("   - 数据库中是否有营养数据")
    print("   - 原料/商品/菜谱 ID 是否存在")
    print("\n2. 如果数据库中没有营养数据，请先导入:")
    print("   - 使用管理员账户登录")
    print("   - 访问 /admin 页面")
    print("   - 使用营养数据导入功能")
    print("\n3. 前端访问路径:")
    print("   - 原料营养: /nutrition/ingredient/{id}")
    print("   - 商品营养: /nutrition/product/{id}")

if __name__ == "__main__":
    main()
