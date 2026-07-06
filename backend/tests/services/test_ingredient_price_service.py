"""统一加权价格服务测试。"""
from decimal import Decimal
from app.services.ingredient_price_service import _aggregate_weighted


def _rec(price, std_qty):
    """造一个最小伪记录对象，仅含聚合所需字段。"""
    class _R:
        pass
    r = _R()
    r.price = Decimal(str(price))
    r.standard_quantity = Decimal(str(std_qty)) if std_qty else None
    return r


def test_aggregate_basic_weighted_average():
    # 商品A 单价 10 权重 50；商品B 单价 30 权重 50 → (10+30)/2 = 20
    res = _aggregate_weighted(
        product_records={
            1: ([_rec(10, 1)], 50, {"product_id": 1, "name": "A"}),
            2: ([_rec(30, 1)], 50, {"product_id": 2, "name": "B"}),
        },
    )
    assert float(res["unit_price"]) == 20.0
    assert res["mode"] == "weighted"
    assert len(res["participants"]) == 2


def test_aggregate_weighted_proportional():
    # 商品A 单价 10 权重 75；商品B 单价 30 权重 25 → (10*75+30*25)/100 = 15
    res = _aggregate_weighted({
        1: ([_rec(10, 1)], 75, {"product_id": 1, "name": "A"}),
        2: ([_rec(30, 1)], 25, {"product_id": 2, "name": "B"}),
    })
    assert float(res["unit_price"]) == 15.0


def test_aggregate_weight_zero_excluded():
    # 权重 0 的商品被排除，仅在剩余商品间归一
    res = _aggregate_weighted({
        1: ([_rec(10, 1)], 0, {"product_id": 1, "name": "A"}),
        2: ([_rec(30, 1)], 50, {"product_id": 2, "name": "B"}),
    })
    assert float(res["unit_price"]) == 30.0
    assert len(res["participants"]) == 1
    assert res["excluded"][0]["reason"] == "weight_zero"


def test_aggregate_no_records_excluded_and_renormalize():
    # 商品A 无记录 → 排除；仅商品B 参与并退化
    res = _aggregate_weighted({
        1: ([], 50, {"product_id": 1, "name": "A"}),
        2: ([_rec(30, 1)], 50, {"product_id": 2, "name": "B"}),
    })
    assert float(res["unit_price"]) == 30.0
    assert res["mode"] == "single"
    assert res["excluded"][0]["reason"] == "no_record"


def test_aggregate_single_product_degenerates():
    res = _aggregate_weighted({1: ([_rec(12, 1)], 50, {"product_id": 1, "name": "A"})})
    assert float(res["unit_price"]) == 12.0
    assert res["mode"] == "single"


def test_aggregate_all_empty_returns_none():
    res = _aggregate_weighted({
        1: ([], 50, {"product_id": 1, "name": "A"}),
        2: ([], 50, {"product_id": 2, "name": "B"}),
    })
    assert res["unit_price"] is None
    assert res["mode"] == "none"


def test_aggregate_intra_product_average_before_weighting():
    # 商品A 两条记录（10、20）均价 15；商品B 一条 30；等权 → (15+30)/2 = 22.5
    # 关键：记录数不再放大 A 的权重（旧逻辑会变 (10+20+30)/3=20，错误）
    res = _aggregate_weighted({
        1: ([_rec(10, 1), _rec(20, 1)], 50, {"product_id": 1, "name": "A"}),
        2: ([_rec(30, 1)], 50, {"product_id": 2, "name": "B"}),
    })
    assert abs(float(res["unit_price"]) - 22.5) < 1e-9


def test_aggregate_zero_std_qty_fallback():
    # standard_quantity 为 0/None 时，单价 = price（与 price_aggregator 兜底一致）
    res = _aggregate_weighted({1: ([_rec(8, 0)], 50, {"product_id": 1, "name": "A"})})
    assert float(res["unit_price"]) == 8.0


from app.services.ingredient_price_service import _resolve_weight


class _P:
    """伪 Product。"""
    def __init__(self, pid, pw=50):
        self.id = pid
        self.price_weight = pw


def test_resolve_weight_override_wins():
    # 有用户覆盖 → 用覆盖
    class _Sess:
        def query(self, m):
            class _Q:
                def filter(self, *a):
                    return self
                def first(self):
                    return type("O", (), {"weight": 80})()
            return _Q()
    assert _resolve_weight(_Sess(), user_id=1, product=_P(1, pw=50)) == 80


def test_resolve_weight_global_when_no_override():
    # 无覆盖 → 用 product.price_weight
    class _Sess:
        def query(self, m):
            class _Q:
                def filter(self, *a):
                    return self
                def first(self):
                    return None
            return _Q()
    assert _resolve_weight(_Sess(), user_id=1, product=_P(1, pw=73)) == 73


def test_resolve_weight_default_when_global_none():
    # 全局为 None → 兜底 50
    class _Sess:
        def query(self, m):
            class _Q:
                def filter(self, *a):
                    return self
                def first(self):
                    return None
            return _Q()
    assert _resolve_weight(_Sess(), user_id=1, product=_P(1, pw=None)) == 50


# ===== 集成测试：编排函数 get_weighted_ingredient_price（真实 db）=====
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # 确保所有模型注册到 Base.metadata，create_all 才能建全表
from app.core.database import Base
from app.models.product_entity import Product
from app.models.nutrition import Ingredient
from app.models.product import ProductRecord
from app.services.ingredient_price_service import get_weighted_ingredient_price


@pytest.fixture(scope="module")
def db():
    # 独立 in-memory SQLite，不碰开发库（遵守 CLAUDE.md「不自行修改数据库」）
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    try:
        yield s
    finally:
        s.close()


def _seed(db, ing_name, products_spec):
    """products_spec: [(name, weight, [(price, std_qty)])]"""
    ing = Ingredient(name=ing_name, is_active=True)
    db.add(ing)
    db.flush()
    for pname, w, recs in products_spec:
        p = Product(name=pname, ingredient_id=ing.id, is_active=True, price_weight=w)
        db.add(p)
        db.flush()
        for price, sq in recs:
            db.add(ProductRecord(
                user_id=1, product_id=p.id, product_name=pname,
                price=price, original_quantity=500, original_unit_id=3,
                standard_quantity=sq, standard_unit_id=3,
                recorded_at=datetime(2026, 7, 6, 12, 0), is_active=True,
            ))
    db.commit()
    return ing.id


def test_get_weighted_as_of_mode(db):
    ing_id = _seed(db, "TSK_番茄", [
        ("TSK_普通", 50, [(10, 500)]),
        ("TSK_有机", 50, [(30, 500)]),
    ])
    res = get_weighted_ingredient_price(
        db, ing_id, as_of_date=datetime(2026, 7, 6), user_id=1,
        target_unit_abbr="克", mode="as_of",
    )
    assert res["unit_price"] is not None
    # 10/500=0.02；30/500=0.06；等权 → 0.04
    assert abs(res["unit_price"] - 0.04) < 1e-6
    assert res["mode"] == "weighted"
    assert {p["name"] for p in res["participants"]} == {"TSK_普通", "TSK_有机"}


def test_get_weighted_user_override(db):
    ing_id = _seed(db, "TSK_茄子", [
        ("TSK_普通", 50, [(10, 500)]),
        ("TSK_有机", 50, [(30, 500)]),
    ])
    from app.models.user_product_weight_override import UserProductWeightOverride
    organic = db.query(Product).filter(
        Product.ingredient_id == ing_id,
        Product.name == "TSK_有机",
    ).first()
    db.add(UserProductWeightOverride(user_id=1, product_id=organic.id, weight=0, is_active=True))
    db.commit()
    res = get_weighted_ingredient_price(
        db, ing_id, as_of_date=datetime(2026, 7, 6), user_id=1,
        target_unit_abbr="克", mode="as_of",
    )
    assert res["mode"] == "single"
    assert res["participants"][0]["name"] == "TSK_普通"


def test_admin_global_weight_applies(db):
    # 管理员把某商品全局权重改为 0 → 所有用户视角下该商品被排除
    ing_id = _seed(db, "TSK_葱", [
        ("TSK_红葱", 0, [(5, 500)]),     # 全局权重 0
        ("TSK_白葱", 50, [(8, 500)]),
    ])
    res = get_weighted_ingredient_price(
        db, ing_id, as_of_date=datetime(2026, 7, 6), user_id=999,
        target_unit_abbr="克", mode="as_of",
    )
    assert res["mode"] == "single"
    assert res["participants"][0]["name"] == "TSK_白葱"


def test_different_users_see_different_price(db):
    ing_id = _seed(db, "TSK_蒜", [
        ("TSK_普通", 50, [(10, 500)]),
        ("TSK_有机", 50, [(30, 500)]),
    ])
    from app.models.user_product_weight_override import UserProductWeightOverride
    organic_id = db.query(Product).filter(
        Product.ingredient_id == ing_id, Product.name == "TSK_有机",
    ).first().id
    # 用户 1 把有机权重覆盖为 0
    db.add(UserProductWeightOverride(user_id=1, product_id=organic_id, weight=0, is_active=True))
    db.commit()
    r1 = get_weighted_ingredient_price(
        db, ing_id, as_of_date=datetime(2026, 7, 6), user_id=1,
        target_unit_abbr="克", mode="as_of",
    )
    r2 = get_weighted_ingredient_price(
        db, ing_id, as_of_date=datetime(2026, 7, 6), user_id=2,
        target_unit_abbr="克", mode="as_of",
    )
    # 用户1：仅普通 → 0.02；用户2：等权 → 0.04
    assert abs(r1["unit_price"] - 0.02) < 1e-6
    assert abs(r2["unit_price"] - 0.04) < 1e-6
    db.query(UserProductWeightOverride).filter(UserProductWeightOverride.user_id == 1).delete()
    db.commit()
