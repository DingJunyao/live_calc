"""recipe_edit 执行器：snapshot 存旧食材 + revert 食材回滚 单元测试。

直接用 db_session 内存库测执行器，不经 API 层（范式同 test_entity_executors.py）。
"""
from types import SimpleNamespace

from app.models.recipe import Recipe, RecipeIngredient
from app.models.nutrition import Ingredient
from app.models.unit import Unit
from app.services.proposals.executors.recipe_edit import RecipeEditExecutor


def _proposal(entity_id, update_data):
    return SimpleNamespace(
        id=88001, action="update", entity_id=entity_id,
        payload={"update_data": update_data}, snapshot=None, revert_payload=None,
        proposer_id=1,
    )


def _seed_recipe(db, rid=88001):
    """建一条菜谱 + 两个食材 + 一条旧食材引用，独立大 id 隔离残留。"""
    ing_a = db.query(Ingredient).filter(Ingredient.name == "测试原料A_88001").first()
    if ing_a is None:
        ing_a = Ingredient(name="测试原料A_88001", is_active=True)
        db.add(ing_a); db.flush()
    ing_b = db.query(Ingredient).filter(Ingredient.name == "测试原料B_88001").first()
    if ing_b is None:
        ing_b = Ingredient(name="测试原料B_88001", is_active=True)
        db.add(ing_b); db.flush()
    r = db.query(Recipe).filter(Recipe.id == rid).first()
    if r is None:
        r = Recipe(id=rid, name="测试菜谱_88001", servings=2)
        db.add(r); db.flush()
    # 清旧引用，建一条「旧食材」
    db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == rid).delete()
    db.add(RecipeIngredient(
        recipe_id=rid, ingredient_id=ing_a.id, quantity="100", unit_id=None,
        is_optional=False, note="旧备注"))
    db.commit()
    return rid, ing_a.id, ing_b.id


def test_apply_snapshot_includes_old_ingredients(db_session):
    rid, ing_a_id, ing_b_id = _seed_recipe(db_session)
    ex = RecipeEditExecutor()
    p = _proposal(rid, {
        "ingredients": [
            {"ingredient_name": "测试原料B_88001", "quantity": "200"},
        ]
    })
    result = ex.apply(db_session, p)
    db_session.commit()

    snap = result.snapshot
    assert "old_ingredients" in snap
    old = snap["old_ingredients"]
    assert len(old) == 1
    assert old[0]["ingredient_name"] == "测试原料A_88001"
    assert old[0]["quantity"] == "100"


def test_revert_restores_ingredients(db_session):
    rid, ing_a_id, ing_b_id = _seed_recipe(db_session)
    ex = RecipeEditExecutor()
    p = _proposal(rid, {
        "name": "改名了",
        "servings": 5,
        "ingredients": [
            {"ingredient_name": "测试原料B_88001", "quantity": "200"},
        ]
    })
    result = ex.apply(db_session, p)
    p.snapshot = result.snapshot
    p.revert_payload = result.revert_payload
    db_session.commit()

    rows = db_session.query(RecipeIngredient).filter(
        RecipeIngredient.recipe_id == rid).all()
    assert len(rows) == 1 and rows[0].ingredient_id == ing_b_id

    ex.revert(db_session, p)
    db_session.commit()

    rows = db_session.query(RecipeIngredient).filter(
        RecipeIngredient.recipe_id == rid).all()
    assert len(rows) == 1
    assert rows[0].ingredient_id == ing_a_id
    assert rows[0].quantity == "100"

    # 标量字段回滚（顺带覆盖 DateTime/Date 跳过分支：updated_at/created_at 不回滚）
    recipe = db_session.query(Recipe).filter(Recipe.id == rid).first()
    assert recipe.name == "测试菜谱_88001"
    assert recipe.servings == 2


def test_build_snapshot_prefills_old_ingredients(db_session):
    """submit 时预填 snapshot（供 pending 审核看旧食材）。"""
    rid, _, _ = _seed_recipe(db_session)
    ex = RecipeEditExecutor()
    p = _proposal(rid, {"name": "改个名"})
    snap = ex.build_snapshot(db_session, p)
    assert "old_ingredients" in snap
    assert len(snap["old_ingredients"]) == 1
