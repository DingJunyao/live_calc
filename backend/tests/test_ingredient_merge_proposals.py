"""ingredient merge 执行器：snapshot 迁移明细含可读名 单元测试。"""
from types import SimpleNamespace

from app.models.recipe import Recipe, RecipeIngredient
from app.models.nutrition import Ingredient
from app.models.product_entity import Product
from app.models.product_ingredient_link import ProductIngredientLink
from app.services.proposals.executors.ingredient import IngredientExecutor


def _seed(db, sid=770201, tid=770202, rid=770203, pid=770204):
    src = Ingredient(id=sid, name="源原料_770201", is_active=True)
    tgt = Ingredient(id=tid, name="目标原料_770202", is_active=True)
    db.add_all([src, tgt]); db.flush()
    recipe = Recipe(id=rid, name="受影响菜谱_770203", servings=1)
    db.add(recipe); db.flush()
    db.add(RecipeIngredient(recipe_id=rid, ingredient_id=sid,
                            quantity="50", is_optional=False))
    prod = Product(id=pid, name="关联商品_770204", ingredient_id=sid, is_active=True)
    db.add(prod); db.flush()
    db.add(ProductIngredientLink(product_id=pid, ingredient_id=sid))
    db.commit()
    return sid, tid, rid, pid


def test_merge_snapshot_has_readable_names(db_session):
    sid, tid, rid, pid = _seed(db_session)
    ex = IngredientExecutor()
    p = SimpleNamespace(
        id=770210, action="merge", entity_id=None,
        payload={"source_ids": [sid], "target_id": tid},
        snapshot=None, revert_payload=None, proposer_id=1,
    )
    result = ex.apply(db_session, p)
    db_session.commit()
    snap = result.snapshot

    assert snap["target_name"] == "目标原料_770202"
    ri = snap["recipe_ingredients"][0]
    assert ri["recipe_name"] == "受影响菜谱_770203"
    pl = snap["product_links"][0]
    assert pl["product_name"] == "关联商品_770204"
