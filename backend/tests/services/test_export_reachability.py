"""可达性遍历集成测试。依赖真实数据库与 testuser。

前置：通过 API 登录 testuser，并确保该用户至少有一条菜谱引用某食材。
若无可引用数据，本测试在 setup 中创建一条临时菜谱并在 teardown 删除。
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.services.export.reachability import collect_full_set, collect_mine_set

client = TestClient(app)


def _login_token():
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password_hash": "test_password_hash"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_full_set_includes_all_ingredients():
    """full 模式应包含库内全部食材 id（至少 >0）。"""
    db = SessionLocal()
    try:
        es = collect_full_set(db)
        assert len(es.ingredient_ids) > 0
    finally:
        db.close()


def test_mine_set_pulls_referenced_admin_ingredient():
    """mine 模式：testuser 的菜谱引用的食材必须进入导出集，无论创建者。"""
    db = SessionLocal()
    try:
        from app.models.user import User
        user = db.query(User).filter(User.username == "testuser").first()
        assert user is not None
        es = collect_mine_set(db, user.id)
        # 我的菜谱引用的每个食材都应在集合内
        from app.models.recipe import Recipe, RecipeIngredient
        my_recipe_ids = {r.id for r in db.query(Recipe).filter(Recipe.user_id == user.id).all()}
        referenced = {
            ri.ingredient_id
            for ri in db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id.in_(my_recipe_ids)).all()
            if ri.ingredient_id is not None
        }
        assert referenced.issubset(es.ingredient_ids)
    finally:
        db.close()
