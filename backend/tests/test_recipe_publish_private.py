"""菜谱发布默认私有 · 创建与可见性测试。

方案 A：自创菜谱默认 is_public=False（含管理员），点「发布」按钮才公开。
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.proposals.registry import ExecutorRegistry
from app.services.proposals.bootstrap import register_all

client = TestClient(app)


@pytest.fixture(autouse=True)
def _register_executors():
    """注册业务执行器（TestClient 不触发 main.py lifespan，故显式注册一次）。"""
    if not ExecutorRegistry.get("ingredient"):
        register_all()
    yield


def _recipe_payload(name="测试菜谱"):
    return {
        "name": name,
        "cooking_steps": [{"step": 1, "content": "做菜"}],
        "ingredients": [],
    }


@pytest.mark.usefixtures("as_non_admin")
def test_create_recipe_private_for_normal_user():
    """普通用户创建菜谱，默认私有。"""
    resp = client.post("/api/v1/recipes", json=_recipe_payload("普通用户菜谱"))
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_public"] is False


@pytest.mark.usefixtures("as_admin")
def test_create_recipe_private_for_admin():
    """管理员创建菜谱，也应默认私有（去掉「管理员即发布」）。"""
    resp = client.post("/api/v1/recipes", json=_recipe_payload("管理员菜谱"))
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_public"] is False


def test_import_recipe_sets_public():
    """所有导入路径创建 Recipe 时必须显式 is_public=True（导入菜谱默认公共）。"""
    import pathlib
    root = pathlib.Path("app/services")
    files = [
        "recipe_import_service.py",
        "importer/importers/howtocook.py",
        "importer/importers/export.py",
        "enhanced_recipe_import_service.py",
        "json_recipe_import_service.py",
    ]
    for rel in files:
        txt = (root / rel).read_text(encoding="utf-8")
        assert "is_public=True" in txt, f"{rel} 创建 Recipe 未设 is_public=True"


@pytest.mark.usefixtures("as_non_admin")
def test_private_recipe_not_visible_to_others(db_session):
    """用户 A(id=1) 的私有 custom 菜谱，用户 B(id=2, non-admin) 在列表/详情看不到。"""
    from app.models.recipe import Recipe
    r = Recipe(name="A的私有菜谱", source="custom", is_public=False, user_id=1, servings=1)
    db_session.add(r)
    db_session.commit()

    resp = client.get("/api/v1/recipes")
    ids = [it["id"] for it in resp.json()["items"]]
    assert r.id not in ids

    resp2 = client.get(f"/api/v1/recipes/{r.id}")
    assert resp2.status_code == 404


@pytest.mark.usefixtures("as_non_admin")
def test_public_recipe_visible_to_others(db_session):
    """公共菜谱（is_public=True）对其他用户可见。"""
    from app.models.recipe import Recipe
    r = Recipe(name="公共菜谱", source="json_repo", is_public=True, user_id=1, servings=1)
    db_session.add(r)
    db_session.commit()

    resp = client.get("/api/v1/recipes")
    ids = [it["id"] for it in resp.json()["items"]]
    assert r.id in ids


@pytest.mark.usefixtures("as_admin")
def test_ingredient_recipes_returns_is_public(db_session):
    """get_ingredient_recipes 返回的 item 必须含正确的 is_public（供原料页显示状态）。"""
    from app.models.recipe import Recipe, RecipeIngredient
    from app.models.nutrition import Ingredient
    ing = Ingredient(name="测试原料_相关菜谱")
    db_session.add(ing)
    db_session.flush()
    pub = Recipe(name="公共相关菜谱", source="custom", is_public=True, user_id=1, servings=1)
    priv = Recipe(name="私有相关菜谱", source="custom", is_public=False, user_id=1, servings=1)
    db_session.add_all([pub, priv])
    db_session.flush()
    db_session.add_all([
        RecipeIngredient(recipe_id=pub.id, ingredient_id=ing.id, quantity="100"),
        RecipeIngredient(recipe_id=priv.id, ingredient_id=ing.id, quantity="100"),
    ])
    db_session.commit()

    resp = client.get(f"/api/v1/nutrition/ingredients/{ing.id}/recipes")
    assert resp.status_code == 200, resp.text
    items = {it["id"]: it for it in resp.json()["items"]}
    assert items[pub.id]["is_public"] is True
    assert items[priv.id]["is_public"] is False
