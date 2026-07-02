"""merchant_merge 执行器：snapshot 含 product_name/target_name 单元测试。

验证 MerchantMergeExecutor.apply 返回的 snapshot 字典冗余了：
- target_name：目标商家名（供审核台零查询显示）
- product_records[].product_id / product_name：受影响价格记录的商品 id/名

并验证 revert 在 snapshot 多了非列字段后仍正常（不踩 Task 2 的 **item 重插坑）。
"""
from datetime import date
from types import SimpleNamespace

from app.models.merchant import Merchant
from app.models.product import ProductRecord
from app.models.product_entity import Product
from app.models.nutrition import Ingredient
from app.models.unit import Unit
from app.services.proposals.executors.merchant_merge import MerchantMergeExecutor


def _seed(db, sid=770301, tid=770302, pid=770399, uid=770001, iid=770010):
    # 最小依赖：单位 + 食材 + 商品
    unit = Unit(id=uid, name=f"斤_{uid}", abbreviation=f"斤_{uid}", unit_type="mass")
    ing = Ingredient(id=iid, name=f"测试食材_{iid}")
    db.add_all([unit, ing]); db.flush()
    prod = Product(id=pid, name=f"测试商品_{pid}", ingredient_id=ing.id)
    src = Merchant(id=sid, name="源商家_770301", is_open=True)
    tgt = Merchant(id=tid, name="目标商家_770302", is_open=True)
    db.add_all([prod, src, tgt]); db.flush()
    # 一条价格记录挂在源商家（补全 ProductRecord 所有 NOT NULL 列）
    db.add(ProductRecord(
        product_id=pid, product_name=f"测试商品_{pid}",
        merchant_id=sid, price=9.9, user_id=1,
        original_quantity=1, original_unit_id=unit.id,
        standard_quantity=0.5, standard_unit_id=unit.id,
        record_type="price", currency="CNY",
    ))
    db.commit()
    return sid, tid, pid


def test_merge_snapshot_has_names(db_session):
    sid, tid, pid = _seed(db_session)
    ex = MerchantMergeExecutor()
    p = SimpleNamespace(
        id=770310, action="merge", entity_id=None,
        payload={"source_ids": [sid], "target_id": tid},
        snapshot=None, revert_payload=None, proposer_id=1,
    )
    result = ex.apply(db_session, p)
    db_session.commit()
    snap = result.snapshot

    assert snap["target_name"] == "目标商家_770302"
    pr = snap["product_records"][0]
    assert "product_name" in pr          # 有该键
    assert pr["product_id"] == pid
    assert pr["product_name"] == "测试商品_770399"
    # 保留原键
    assert "id" in pr and "merchant_id" in pr


def test_revert_still_works_afteradding_names(db_session):
    # 用不同 id 避免与 test_merge_snapshot_has_names 共享内存库撞 UNIQUE
    sid, tid, pid = _seed(db_session, sid=770303, tid=770304,
                          pid=770398, uid=770002, iid=770011)
    ex = MerchantMergeExecutor()
    p = SimpleNamespace(
        id=770311, action="merge", entity_id=None,
        payload={"source_ids": [sid], "target_id": tid},
        snapshot=None, revert_payload=None, proposer_id=1,
    )
    result = ex.apply(db_session, p)
    p.snapshot = result.snapshot
    p.revert_payload = result.revert_payload
    db_session.commit()
    ex.revert(db_session, p)
    db_session.commit()
    # revert 后源商家复活
    m = db_session.query(Merchant).get(sid)
    assert m.is_open in (True, 1)
