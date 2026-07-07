"""原料级各商家价格：同商家多商品按权重加权测试（Task 2）。

覆盖 GET /api/v1/nutrition/ingredients/{id}/latest-price-by-merchant：
  - 同一商家下多个商品时，代表价按商品权重加权
  - 权重为 0 的商品被排除
"""
from conftest import TestingSessionLocal, engine, FakeUser
from app.core.database import Base


def _get_or_create_jin(db):
    from app.models.unit import Unit
    u = db.query(Unit).filter(Unit.abbreviation == "斤").first()
    if u:
        return u
    u = Unit(name="斤", abbreviation="斤", unit_type="mass")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _build(db, p1_w, p2_w, p1_price, p2_price):
    """原料 + 2 商品（同 1 商家各 1 条记录）。original 单位 = 斤 = ing_target，免单位转换。"""
    from app.models.nutrition import Ingredient
    from app.models.product_entity import Product
    from app.models.merchant import Merchant
    from app.models.product import ProductRecord

    ing = Ingredient(name="商家加权测试原料")
    db.add(ing)
    db.commit()
    db.refresh(ing)

    p1 = Product(name="商加P1", ingredient_id=ing.id, price_weight=p1_w, is_active=True)
    p2 = Product(name="商加P2", ingredient_id=ing.id, price_weight=p2_w, is_active=True)
    db.add_all([p1, p2])
    db.commit()
    db.refresh(p1)
    db.refresh(p2)

    m = Merchant(user_id=FakeUser.id, name="商加商家", is_open=True)
    db.add(m)
    db.commit()
    db.refresh(m)

    jin = _get_or_create_jin(db)
    for prod, price in [(p1, p1_price), (p2, p2_price)]:
        db.add(ProductRecord(
            user_id=FakeUser.id, product_id=prod.id, product_name=prod.name,
            merchant_id=m.id, price=price, currency="CNY",
            original_quantity=1, original_unit_id=jin.id,
            standard_quantity=1, standard_unit_id=jin.id,
            record_type="price",
        ))
    db.commit()
    return ing.id, m.id


def _cleanup(db, ing_id, m_id):
    from app.models.nutrition import Ingredient
    from app.models.product_entity import Product
    from app.models.merchant import Merchant
    from app.models.product import ProductRecord

    pids = [p.id for p in db.query(Product).filter(Product.ingredient_id == ing_id).all()]
    if pids:
        db.query(ProductRecord).filter(ProductRecord.product_id.in_(pids)).delete(synchronize_session=False)
    db.query(Product).filter(Product.ingredient_id == ing_id).delete(synchronize_session=False)
    db.query(Ingredient).filter(Ingredient.id == ing_id).delete(synchronize_session=False)
    db.query(Merchant).filter(Merchant.id == m_id).delete(synchronize_session=False)
    db.commit()


def test_same_merchant_multi_product_weighted(as_admin):
    from starlette.testclient import TestClient
    from app.main import app

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    ing_id = m_id = None
    try:
        ing_id, m_id = _build(db, p1_w=30, p2_w=70, p1_price=10, p2_price=20)
    finally:
        db.close()

    client = TestClient(app)
    try:
        r = client.get(f"/api/v1/nutrition/ingredients/{ing_id}/latest-price-by-merchant")
        assert r.status_code == 200
        prices = r.json()["prices"]
        assert len(prices) == 1
        # 加权 = (10*30 + 20*70) / 100 = 17.0
        assert abs(prices[0]["price"] - 17.0) < 0.01
    finally:
        db = TestingSessionLocal()
        try:
            if ing_id and m_id:
                _cleanup(db, ing_id, m_id)
        finally:
            db.close()


def test_weight_zero_product_excluded_from_merchant(as_admin):
    from starlette.testclient import TestClient
    from app.main import app

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    ing_id = m_id = None
    try:
        # P1 权重 0（排除），P2 权重 50 → 代表价 = P2 单价 = 20
        ing_id, m_id = _build(db, p1_w=0, p2_w=50, p1_price=10, p2_price=20)
    finally:
        db.close()

    client = TestClient(app)
    try:
        r = client.get(f"/api/v1/nutrition/ingredients/{ing_id}/latest-price-by-merchant")
        assert r.status_code == 200
        prices = r.json()["prices"]
        assert len(prices) == 1
        assert abs(prices[0]["price"] - 20.0) < 0.01
    finally:
        db = TestingSessionLocal()
        try:
            if ing_id and m_id:
                _cleanup(db, ing_id, m_id)
        finally:
            db.close()
