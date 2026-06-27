"""商家执行器：CRUD。delete 处理 ProductRecord.merchant_id 引用（置 NULL）。

Merchant 无 is_active，软删用 is_open=False + 名称加后缀标记；
ProductRecord.merchant_id 可空，删商家时把引用置 NULL，revert 还原。
"""
from fastapi import HTTPException

from app.services.proposals.base import ApplyResult
from app.services.proposals.executors._crud_base import CrudExecutorBase
from app.models.merchant import Merchant
from app.models.product import ProductRecord

_MERGED_PREFIX = "[已停用] "


class MerchantExecutor(CrudExecutorBase):
    entity_type = "merchant"
    model_class = Merchant

    def apply(self, db, proposal) -> ApplyResult:
        # delete 走自定义路径（需快照 ProductRecord 引用）
        if proposal.action == "delete":
            return self._apply_delete(db, proposal)
        return super().apply(db, proposal)

    def _apply_delete(self, db, proposal) -> ApplyResult:
        eid = proposal.entity_id
        m = db.query(Merchant).get(eid)
        if m is None:
            raise HTTPException(status_code=404, detail=f"商家 {eid} 不存在")
        snapshot = {
            "merchant": {c.name: getattr(m, c.name) for c in m.__table__.columns},
            "product_records": [
                {"id": r.id, "merchant_id": r.merchant_id}
                for r in db.query(ProductRecord)
                    .filter(ProductRecord.merchant_id == eid).all()
            ],
        }
        # 引用置 NULL
        db.query(ProductRecord).filter(
            ProductRecord.merchant_id == eid
        ).update({ProductRecord.merchant_id: None}, synchronize_session=False)
        # 软停用
        m.is_open = False
        if not m.name.startswith(_MERGED_PREFIX):
            m.name = f"{_MERGED_PREFIX}{m.name}"
        return ApplyResult(
            snapshot=snapshot,
            revert_payload={"restore_merchant": True},
            summary=f"已停用商家 {eid}（引用置 NULL）",
        )

    def revert(self, db, proposal) -> None:
        if proposal.action == "delete":
            self._revert_delete(db, proposal)
            return
        super().revert(db, proposal)

    def _revert_delete(self, db, proposal) -> None:
        snap = proposal.snapshot or {}
        eid = proposal.entity_id
        m = db.query(Merchant).get(eid)
        if m is not None:
            msnap = snap.get("merchant", {})
            for k, v in msnap.items():
                setattr(m, k, v)
        # 还原 ProductRecord 引用
        for item in snap.get("product_records", []):
            r = db.query(ProductRecord).get(item["id"])
            if r is not None:
                r.merchant_id = item["merchant_id"]
