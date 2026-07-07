"""原料下商品批量生效权重端点测试（Task 1）。

覆盖 GET /api/v1/nutrition/ingredients/{id}/product-weights：
  - 覆盖权重优先于全局
  - 未覆盖商品回落全局
  - 无商品的原料返回空列表
"""
from conftest import TestingSessionLocal, engine, FakeUser
from app.core.database import Base


def _build(db, weights: dict, override: dict | None = None):
    """建原料 + 商品（price_weight 由 weights 给），可选当前用户覆盖。返回 (ing_id, pids)。"""
    from app.models.nutrition import Ingredient
    from app.models.product_entity import Product
    from app.models.user_product_weight_override import UserProductWeightOverride

    ing = Ingredient(name="加权测试原料")
    db.add(ing)
    db.commit()
    db.refresh(ing)

    pids = {}
    for name, w in weights.items():
        p = Product(name=name, ingredient_id=ing.id, price_weight=w, is_active=True)
        db.add(p)
        db.commit()
        db.refresh(p)
        pids[name] = p.id

    if override:
        for name, w in override.items():
            db.add(UserProductWeightOverride(
                user_id=FakeUser.id, product_id=pids[name], weight=w, is_active=True,
            ))
        db.commit()
    return ing.id, pids


def _cleanup(db, ing_id: int, pids: dict):
    from app.models.nutrition import Ingredient
    from app.models.product_entity import Product
    from app.models.user_product_weight_override import UserProductWeightOverride

    if pids:
        db.query(UserProductWeightOverride).filter(
            UserProductWeightOverride.product_id.in_(list(pids.values()))
        ).delete(synchronize_session=False)
    db.query(Product).filter(Product.ingredient_id == ing_id).delete(synchronize_session=False)
    db.query(Ingredient).filter(Ingredient.id == ing_id).delete(synchronize_session=False)
    db.commit()


def test_product_weights_override_beats_global(as_admin):
    from starlette.testclient import TestClient
    from app.main import app

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    ing_id = pids = None
    try:
        ing_id, pids = _build(db, {"P1": 30, "P2": 60}, override={"P2": 70})
    finally:
        db.close()

    client = TestClient(app)
    try:
        r = client.get(f"/api/v1/nutrition/ingredients/{ing_id}/product-weights")
        assert r.status_code == 200
        items = r.json()["items"]
        by_name = {it["name"]: it for it in items}
        # P1 未覆盖 → 全局 30
        assert by_name["P1"]["effective_weight"] == 30
        assert by_name["P1"]["global_weight"] == 30
        assert by_name["P1"]["override_weight"] is None
        assert by_name["P1"]["source"] == "global"
        # P2 有覆盖 → 覆盖 70 优先
        assert by_name["P2"]["effective_weight"] == 70
        assert by_name["P2"]["global_weight"] == 60
        assert by_name["P2"]["override_weight"] == 70
        assert by_name["P2"]["source"] == "override"
    finally:
        db = TestingSessionLocal()
        try:
            if ing_id and pids:
                _cleanup(db, ing_id, pids)
        finally:
            db.close()


def test_product_weights_empty_ingredient(as_admin):
    from starlette.testclient import TestClient
    from app.main import app
    from app.models.nutrition import Ingredient

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    ing_id = None
    try:
        ing = Ingredient(name="空原料")
        db.add(ing)
        db.commit()
        db.refresh(ing)
        ing_id = ing.id
    finally:
        db.close()

    client = TestClient(app)
    try:
        r = client.get(f"/api/v1/nutrition/ingredients/{ing_id}/product-weights")
        assert r.status_code == 200
        assert r.json()["items"] == []
    finally:
        db = TestingSessionLocal()
        try:
            db.query(Ingredient).filter(Ingredient.id == ing_id).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()


def test_product_weights_falls_back_to_default(as_admin):
    """商品 price_weight 为 None 时兜底 50。"""
    from starlette.testclient import TestClient
    from app.main import app

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    ing_id = pids = None
    try:
        # weights 传 None 模拟未设全局权重
        ing_id, pids = _build(db, {"P3": None})
    finally:
        db.close()

    client = TestClient(app)
    try:
        r = client.get(f"/api/v1/nutrition/ingredients/{ing_id}/product-weights")
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) == 1
        assert items[0]["effective_weight"] == 50
        assert items[0]["source"] == "global"
    finally:
        db = TestingSessionLocal()
        try:
            if ing_id and pids:
                _cleanup(db, ing_id, pids)
        finally:
            db.close()
