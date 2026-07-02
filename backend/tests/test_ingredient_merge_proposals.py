"""ingredient merge 执行器：snapshot 迁移明细含可读名 单元测试。"""
from types import SimpleNamespace

from app.models.recipe import Recipe, RecipeIngredient
from app.models.nutrition import Ingredient, IngredientNutritionMapping
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


def test_merge_revert_restores_rows(db_session):
    """regress f7a6734：snapshot 带 recipe_name/product_name/nutrition_name 后，
    revert 在受影响行被合并删除（非就地改 ingredient_id）时需重新插入，
    `**item` 崩溃：TypeError: invalid keyword argument。

    构造「目标已存在同 recipe/product/nutrition 行」场景 → 合并走删除分支 →
    revert 必须重新插入源行，正是触发 **item 崩溃的路径。
    """
    sid = 770301
    tid = 770302
    rid = 770303
    pid = 770304
    nid = 770305

    src = Ingredient(id=sid, name="源_770301", is_active=True)
    tgt = Ingredient(id=tid, name="目标_770302", is_active=True)
    db_session.add_all([src, tgt]); db_session.flush()
    recipe = Recipe(id=rid, name="菜谱_770303", servings=1)
    db_session.add(recipe); db_session.flush()
    # 源 + 目标 各一行同 recipe —— 合并时源行被删除（合并到目标行），revert 须重插
    db_session.add(RecipeIngredient(recipe_id=rid, ingredient_id=sid,
                                    quantity="50", is_optional=False))
    db_session.add(RecipeIngredient(recipe_id=rid, ingredient_id=tid,
                                    quantity="10", is_optional=False))
    prod = Product(id=pid, name="商品_770304", ingredient_id=sid, is_active=True)
    db_session.add(prod); db_session.flush()
    # 源 + 目标 各一条同 product 链接 —— 合并删除源链接，revert 须重插
    db_session.add(ProductIngredientLink(product_id=pid, ingredient_id=sid))
    db_session.add(ProductIngredientLink(product_id=pid, ingredient_id=tid))
    # 源 + 目标 各一条同 nutrition 映射 —— 合并删除源映射，revert 须重插
    from app.models.nutrition_data import NutritionData
    db_session.add(NutritionData(id=nid, ingredient_id=tid, source="custom",
                                 usda_name="测试营养素_770305", nutrients={}))
    db_session.flush()
    db_session.add(IngredientNutritionMapping(ingredient_id=sid, nutrition_id=nid,
                                              priority=1, confidence=0.5))
    db_session.add(IngredientNutritionMapping(ingredient_id=tid, nutrition_id=nid,
                                              priority=1, confidence=0.5))
    db_session.commit()

    ex = IngredientExecutor()
    p = SimpleNamespace(
        id=770310, action="merge", entity_id=None,
        payload={"source_ids": [sid], "target_id": tid},
        snapshot=None, revert_payload=None, proposer_id=1,
    )
    result = ex.apply(db_session, p)
    db_session.commit()
    # snapshot 现已装饰 recipe_name/product_name/nutrition_name
    assert result.snapshot["recipe_ingredients"][0]["recipe_name"] == "菜谱_770303"

    # 回填 snapshot/revert_payload 模拟 service._do_apply 落库
    p.snapshot = result.snapshot
    p.revert_payload = result.revert_payload

    # revert —— 修复前在此崩溃：TypeError: 'recipe_name' is an invalid keyword argument
    ex.revert(db_session, p)
    db_session.commit()

    # 源行已重新插入并指向源食材
    ri_src = db_session.query(RecipeIngredient).filter(
        RecipeIngredient.recipe_id == rid,
        RecipeIngredient.ingredient_id == sid,
    ).all()
    assert len(ri_src) == 1
    pl_src = db_session.query(ProductIngredientLink).filter(
        ProductIngredientLink.product_id == pid,
        ProductIngredientLink.ingredient_id == sid,
    ).all()
    assert len(pl_src) == 1
    nm_src = db_session.query(IngredientNutritionMapping).filter(
        IngredientNutritionMapping.ingredient_id == sid,
        IngredientNutritionMapping.nutrition_id == nid,
    ).all()
    assert len(nm_src) == 1
