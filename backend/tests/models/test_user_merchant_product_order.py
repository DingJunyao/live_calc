# backend/tests/models/test_user_merchant_product_order.py

"""UserMerchantProductOrder 模型 & API 集成测试。"""

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.core.security import get_current_user

# 导入所有需要的模型，确保在 create_all 前注册到 Base.metadata
from app.models import (
    User, Merchant, ProductRecord,
)
from app.models.product_entity import Product
from app.models.nutrition import Ingredient
from app.models.unit import Unit
from app.models.user_merchant_product_order import UserMerchantProductOrder

# 内存库 setup — 先 import 模型再 create_all
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(engine)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class FakeUser:
    id = 1
    username = "testuser"
    email = "test@example.com"
    phone = None
    is_admin = False
    email_verified = True
    created_at = None


def fake_current_user():
    return FakeUser()


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_override():
    """每个测试前后安装/卸载 override。"""
    prev = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = fake_current_user
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(prev)


@pytest.fixture()
def db():
    """提供会话并清理所有数据。"""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
    # 清理所有表
    session = TestingSessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()


@pytest.fixture()
def test_data(db):
    """创建测试用用户、商家、商品。"""
    user = User(id=1, username="testuser", email="test@example.com",
                password_hash="x", is_admin=False)
    ingredient = Ingredient(id=1, name="通用食材")
    merchant = Merchant(id=1, user_id=1, name="测试超市")
    product_a = Product(id=1, name="牛奶", ingredient_id=1)
    product_b = Product(id=2, name="面包", ingredient_id=1)
    product_c = Product(id=3, name="鸡蛋", ingredient_id=1)

    db.add_all([user, ingredient, merchant, product_a, product_b, product_c])
    db.commit()
    return {"merchant_id": 1, "product_ids": [1, 2, 3]}


def _create_price_record(db, uid, mid, pid, price=1.0):
    """辅助：创建一条产品价格记录。"""
    unit = db.query(Unit).filter(Unit.abbreviation == "斤").first()
    if not unit:
        unit = Unit(abbreviation="斤", name="斤", unit_type="mass")
        db.add(unit)
        db.commit()
        db.refresh(unit)
    product = db.query(Product).filter(Product.id == pid).first()
    rec = ProductRecord(
        user_id=uid, merchant_id=mid, product_id=pid,
        product_name=product.name if product else "",
        price=price, original_quantity=1, original_unit_id=unit.id,
        standard_quantity=500, standard_unit_id=unit.id,
        record_type="price",
    )
    db.add(rec)
    db.commit()


class TestSaveProductOrders:
    """测试 POST /api/v1/merchants/{id}/product-orders"""

    def test_save_orders_success(self, db, test_data):
        mid = test_data["merchant_id"]
        pids = test_data["product_ids"]

        resp = client.post(f"/api/v1/merchants/{mid}/product-orders", json={
            "product_ids": pids,
            "session_date": "2026-06-23",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "已保存" in data["message"]

        # 验证数据已写入
        records = db.query(UserMerchantProductOrder).filter(
            UserMerchantProductOrder.merchant_id == mid,
            UserMerchantProductOrder.session_date == date(2026, 6, 23),
        ).order_by(UserMerchantProductOrder.sort_order).all()
        assert len(records) == 3
        assert [r.product_id for r in records] == [1, 2, 3]
        assert [r.sort_order for r in records] == [0, 1, 2]

    def test_save_orders_upsert(self, db, test_data):
        """同一天同商品再次保存应更新 sort_order。"""
        mid = test_data["merchant_id"]

        # 第一次保存
        client.post(f"/api/v1/merchants/{mid}/product-orders", json={
            "product_ids": [1, 2, 3],
            "session_date": "2026-06-23",
        })
        # 第二次保存相同商品但顺序不同
        client.post(f"/api/v1/merchants/{mid}/product-orders", json={
            "product_ids": [3, 2, 1],
            "session_date": "2026-06-23",
        })

        records = db.query(UserMerchantProductOrder).filter(
            UserMerchantProductOrder.merchant_id == mid,
            UserMerchantProductOrder.session_date == date(2026, 6, 23),
        ).order_by(UserMerchantProductOrder.sort_order).all()
        assert len(records) == 3
        assert [(r.product_id, r.sort_order) for r in records] == [(3, 0), (2, 1), (1, 2)]

    def test_save_orders_invalid_date(self, db, test_data):
        mid = test_data["merchant_id"]
        resp = client.post(f"/api/v1/merchants/{mid}/product-orders", json={
            "product_ids": [1, 2],
            "session_date": "2026/06/23",
        })
        assert resp.status_code == 422

    def test_save_orders_merchant_not_found(self, db, test_data):
        resp = client.post("/api/v1/merchants/999/product-orders", json={
            "product_ids": [1, 2],
            "session_date": "2026-06-23",
        })
        assert resp.status_code == 404


class TestCustomSortScore:
    """测试 GET product-prices 返回 custom_sort_score。"""

    def test_custom_sort_score_in_response(self, db, test_data):
        """验证设置了排序分的商品有 custom_sort_score 字段。"""
        mid = test_data["merchant_id"]
        pids = test_data["product_ids"]

        _create_price_record(db, 1, mid, 1)
        _create_price_record(db, 1, mid, 2)
        _create_price_record(db, 1, mid, 3)

        client.post(f"/api/v1/merchants/{mid}/product-orders", json={
            "product_ids": [2, 1, 3],
            "session_date": "2026-06-23",
        })

        resp = client.get(f"/api/v1/merchants/{mid}/product-prices?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        items = data["items"]
        scored = [i for i in items if i["custom_sort_score"] is not None]
        assert len(scored) == 3
        scored_sorted = sorted(scored, key=lambda i: i["custom_sort_score"])
        assert [s["product_id"] for s in scored_sorted] == [2, 1, 3]

    def test_no_custom_score_by_default(self, db, test_data):
        """没有排序记录时 custom_sort_score 为 null。"""
        mid = test_data["merchant_id"]
        _create_price_record(db, 1, mid, 1)

        resp = client.get(f"/api/v1/merchants/{mid}/product-prices?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["custom_sort_score"] is None


class TestWeightedSorting:
    """测试加权排序算法。"""

    def test_three_day_weighted(self, db, test_data):
        """最近 3 天加权后，今天权重最大。"""
        mid = test_data["merchant_id"]

        for pid in [1, 2, 3]:
            _create_price_record(db, 1, mid, pid)

        today = date.today()
        yesterday = today - timedelta(days=1)
        day_before = today - timedelta(days=2)

        orders_data = [
            (1, day_before, 0), (2, day_before, 1),
            (3, yesterday, 0), (1, yesterday, 1),
            (2, today, 0),
        ]
        for pid, sess_date, sort_order in orders_data:
            rec = UserMerchantProductOrder(
                user_id=1, merchant_id=mid, product_id=pid,
                session_date=sess_date, sort_order=sort_order,
            )
            db.add(rec)
        db.commit()

        resp = client.get(f"/api/v1/merchants/{mid}/product-prices?limit=10")
        assert resp.status_code == 200
        items = resp.json()["items"]
        scored = [(i["product_id"], i["custom_sort_score"]) for i in items if i["custom_sort_score"] is not None]

        score_map = {pid: score for pid, score in scored}
        assert score_map[1] == pytest.approx(0.666, abs=0.01)
        assert score_map[2] == pytest.approx(0.25, abs=0.01)
        assert score_map[3] == pytest.approx(0, abs=0.01)

        scored_sorted = sorted(scored, key=lambda x: x[1])
        assert [p[0] for p in scored_sorted] == [3, 2, 1]
