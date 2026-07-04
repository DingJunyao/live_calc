"""商家执行器：CRUD。delete 级联软删 PriceRecord。

Merchant 无 is_active，软删用 is_open=False + 名称加后缀标记；
delete 时级联软删（is_active=False）该商家的所有 ProductRecord，revert 还原。
"""
from fastapi import HTTPException

from app.services.proposals.base import ApplyResult
from app.services.proposals.executors._crud_base import CrudExecutorBase, _json_safe
from app.models.merchant import Merchant
from app.models.product import ProductRecord

_MERGED_PREFIX = "[已停用] "


class MerchantExecutor(CrudExecutorBase):
    entity_type = "merchant"
    model_class = Merchant

    def preview(self, db, proposal) -> dict:
        if proposal.action == "delete":
            eid = proposal.entity_id
            cnt = 0
            if eid:
                cnt = db.query(ProductRecord).filter(
                    ProductRecord.merchant_id == eid
                ).count()
            return {
                "action": "delete",
                "cascade_record_count": cnt,
                "note": f"将级联软删 {cnt} 条价格记录，商家名称加 [已停用] 前缀",
            }
        return super().preview(db, proposal)

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

        record_ids = [
            r.id
            for r in db.query(ProductRecord)
                .filter(ProductRecord.merchant_id == eid).all()
        ]
        snapshot = {
            "merchant": {c.name: _json_safe(getattr(m, c.name)) for c in m.__table__.columns},
            "product_records": [
                {"id": r.id, "merchant_id": r.merchant_id, "is_active": r.is_active}
                for r in db.query(ProductRecord)
                    .filter(ProductRecord.merchant_id == eid).all()
            ],
            "cascade_record_count": len(record_ids),
        }
        # 级联软删 ProductRecord
        if record_ids:
            db.query(ProductRecord).filter(
                ProductRecord.id.in_(record_ids)
            ).update({ProductRecord.is_active: False}, synchronize_session=False)
        # 软停用商家
        m.is_open = False
        if not m.name.startswith(_MERGED_PREFIX):
            m.name = f"{_MERGED_PREFIX}{m.name}"
        return ApplyResult(
            snapshot=snapshot,
            revert_payload={"restore_merchant": True, "cascade_record_ids": record_ids},
            summary=f"已停用商家 {eid}（级联软删 {len(record_ids)} 条价格记录）",
        )

    def revert(self, db, proposal) -> None:
        if proposal.action == "delete":
            self._revert_delete(db, proposal)
            return
        super().revert(db, proposal)

    def _revert_delete(self, db, proposal) -> None:
        snap = proposal.snapshot or {}
        rp = proposal.revert_payload or {}
        eid = proposal.entity_id

        # 还原商家
        m = db.query(Merchant).get(eid)
        if m is not None:
            msnap = snap.get("merchant", {})
            for k, v in msnap.items():
                setattr(m, k, v)

        # 反级联：复活 ProductRecord（还原 is_active + merchant_id）
        for item in snap.get("product_records", []):
            r = db.query(ProductRecord).get(item["id"])
            if r is not None:
                r.merchant_id = item["merchant_id"]
                r.is_active = item.get("is_active", True)
