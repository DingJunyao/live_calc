import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.recipe_service import calculate_recipe_cost
from app.models.user import User
from app.models.recipe import Recipe, RecipeIngredient
from app.models.product_entity import Product
from app.models.product import ProductRecord
from app.models.nutrition import Ingredient
from app.models.unit import Unit
from datetime import datetime
from decimal import Decimal

client = TestClient(app)


def test_create_recipe():
    """测试创建菜谱"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password_hash": "test_password_hash"}
    )
    token = response.json()["access_token"]

    response = client.post(
        "/api/v1/recipes/",
        json={
            "name": "番茄炒蛋",
            "source": "custom",
            "cooking_steps": [
                {"step": 1, "content": "番茄切块，鸡蛋打散"}
            ],
            "ingredients": [
                {"ingredient_name": "鸡蛋", "quantity": "2", "unit": "个"}
            ],
            "servings": 2
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "番茄炒蛋"


def test_get_recipes():
    """测试获取菜谱列表"""
    response = client.get("/api/v1/recipes/")
    assert response.status_code in [200, 401]


def test_get_recipe_cost():
    """测试获取菜谱成本"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password_hash": "test_password_hash"}
    )
    token = response.json()["access_token"]

    response = client.get(
        "/api/v1/recipes/1/cost",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_cross_user_recipe_cost_uses_public_price(db_session):
    """新用户（无价格记录）算菜谱成本，应跨用户使用公开价格（非 0）。

    构造：用户 A 录了某商品价格，用户 B（无任何价格记录）算含该商品的菜谱成本。
    修复前：价格查询按 user_id 过滤 → B 拿不到价 → 成本 0。
    修复后：价格公开，B 用 A 的价算出成本 > 0。
    """
    db = db_session

    # 单位：克（mass，SI 基准）
    gram = Unit(
        name="test_gram_cross",
        abbreviation="tgc",
        unit_type="mass",
        si_factor=1.0,
        is_si_base=True,
        is_standard=True,
    )
    db.add(gram)
    db.flush()

    # 两个用户
    user_a = User(username="cross_user_a", email="cross_a@test.local", password_hash="x")
    user_b = User(username="cross_user_b", email="cross_b@test.local", password_hash="x")
    db.add_all([user_a, user_b])
    db.flush()

    # 食材 + 商品
    ingredient = Ingredient(name="跨用户测试食材", default_unit_id=gram.id)
    db.add(ingredient)
    db.flush()
    product = Product(name="跨用户测试商品", ingredient_id=ingredient.id)
    db.add(product)
    db.flush()

    # 仅用户 A 录价格：10 元 / 100 克 = 0.1 元/克，今天记录
    record = ProductRecord(
        user_id=user_a.id,
        product_id=product.id,
        product_name=product.name,
        price=Decimal("10.00"),
        original_quantity=100,
        original_unit_id=gram.id,
        standard_quantity=100,
        standard_unit_id=gram.id,
        record_type="price",
        recorded_at=datetime.now(),
    )
    db.add(record)

    # 菜谱（属于 B 也可，可见性由 API 层处理，此处直接给 id）
    recipe = Recipe(name="跨用户成本测试菜谱", servings=1, user_id=user_b.id)
    db.add(recipe)
    db.flush()
    ri = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ingredient.id,
        quantity="100",
        unit_id=gram.id,
    )
    db.add(ri)
    db.commit()

    # 以用户 B 身份算成本（B 无任何价格记录）
    result = await calculate_recipe_cost(recipe.id, user_b.id, db)

    assert result is not None, "calculate_recipe_cost 不应返回 None"
    total = result["total_cost"]
    assert isinstance(total, (Decimal, float, int)), f"total_cost 类型异常: {type(total)}"
    assert float(total) > 0, f"跨用户成本应为正（公开价格），实际: {total}"

    # 清理本次测试数据，避免污染共享内存库的其他测试
    db.query(RecipeIngredient).filter_by(id=ri.id).delete()
    db.query(Recipe).filter_by(id=recipe.id).delete()
    db.query(ProductRecord).filter_by(id=record.id).delete()
    db.query(Product).filter_by(id=product.id).delete()
    db.query(Ingredient).filter_by(id=ingredient.id).delete()
    db.query(User).filter(User.id.in_([user_a.id, user_b.id])).delete()
    db.query(Unit).filter_by(id=gram.id).delete()
    db.commit()

