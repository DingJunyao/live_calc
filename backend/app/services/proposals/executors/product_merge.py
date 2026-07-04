"""商品合并执行器：源商品的价格记录迁移到目标商品，软删源商品。

payload: { target_product_id: int }
entity_id: source_product_id
"""
from typing import Optional

from fastapi import HTTPException

from app.services.proposals.base import ApplyResult, ProposalExecutor


class ProductMergeExecutor(ProposalExecutor):
    entity_type = "product_merge"

    def entity_label(self, db, proposal) -> Optional[str]:
        from app.models.product_entity import Product
        eid = proposal.entity_id
        p = db.query(Product).get(eid) if eid else None
        return f"商品「{p.name}」" if p else None

    def build_snapshot(self, db, proposal) -> dict:
        from app.models.product_entity import Product
        from app.models.product import ProductRecord
        eid = proposal.entity_id
        target_id = (proposal.payload or {}).get("target_product_id")
        src = db.query(Product).get(eid) if eid else None
        tgt = db.query(Product).get(target_id) if target_id else None
        pr_cnt = 0
        if eid:
            pr_cnt = db.query(ProductRecord).filter(
                ProductRecord.product_id == eid,
                ProductRecord.is_active == True,
            ).count()
        return {
            "source_name": src.name if src else "?",
            "target_name": tgt.name if tgt else "?",
            "affected_records_count": pr_cnt,
        }

    def validate(self, db, proposal) -> None:
        from app.models.product_entity import Product
        eid = proposal.entity_id
        payload = proposal.payload or {}
        target_id = payload.get("target_product_id")
        if eid is None or target_id is None:
            raise HTTPException(status_code=400, detail="需要源商品 ID 和目标商品 ID")
        if eid == target_id:
            raise HTTPException(status_code=400, detail="不能合并到自身")

        src = db.query(Product).filter(
            Product.id == eid, Product.is_active == True
        ).first()
        if src is None:
            raise HTTPException(status_code=404, detail="源商品不存在或已删除")

        tgt = db.query(Product).filter(
            Product.id == target_id, Product.is_active == True
        ).first()
        if tgt is None:
            raise HTTPException(status_code=404, detail="目标商品不存在或已删除")

        if src.ingredient_id != tgt.ingredient_id:
            raise HTTPException(
                status_code=400, detail="只能合并同一原料下的商品"
            )

    def preview(self, db, proposal) -> dict:
        from app.models.product_entity import Product
        from app.models.product import ProductRecord
        eid = proposal.entity_id
        target_id = (proposal.payload or {}).get("target_product_id")
        src = db.query(Product).get(eid) if eid else None
        tgt = db.query(Product).get(target_id) if target_id else None
        pr_cnt = 0
        if eid:
            pr_cnt = db.query(ProductRecord).filter(
                ProductRecord.product_id == eid,
                ProductRecord.is_active == True,
            ).count()
        return {
            "source": src.name if src else "?",
            "target": tgt.name if tgt else "?",
            "affected_price_records": pr_cnt,
            "note": "价格记录将迁移到目标商品，源商品将被软删除",
        }

    def apply(self, db, proposal) -> ApplyResult:
        from app.models.product_entity import Product
        from app.models.product import ProductRecord

        eid = proposal.entity_id
        target_id = (proposal.payload or {}).get("target_product_id")

        src = db.query(Product).filter(
            Product.id == eid, Product.is_active == True
        ).first()
        tgt = db.query(Product).filter(
            Product.id == target_id, Product.is_active == True
        ).first()
        if not src or not tgt:
            raise HTTPException(status_code=404, detail="源商品或目标商品不存在")

        # 快照
        record_ids = [
            r.id
            for r in db.query(ProductRecord)
            .filter(ProductRecord.product_id == eid, ProductRecord.is_active == True)
            .all()
        ]
        snapshot = {
            "source_id": eid,
            "source_is_active": True,
            "target_id": target_id,
            "source_name": src.name,
            "target_name": tgt.name,
        }

        # 迁移价格记录
        if record_ids:
            db.query(ProductRecord).filter(
                ProductRecord.id.in_(record_ids)
            ).update({ProductRecord.product_id: target_id}, synchronize_session=False)

        # 软删源商品
        src.is_active = False

        return ApplyResult(
            snapshot=snapshot,
            revert_payload={"record_ids": record_ids, "source_id": eid},
            summary=f"已合并到「{tgt.name}」（迁移 {len(record_ids)} 条价格记录）",
        )

    def revert(self, db, proposal) -> None:
        from app.models.product_entity import Product
        from app.models.product import ProductRecord

        rp = proposal.revert_payload or {}
        snap = proposal.snapshot or {}

        record_ids = rp.get("record_ids") or snap.get("record_ids") or []
        source_id = rp.get("source_id") or snap.get("source_id")

        # 还原价格记录到源商品
        if record_ids and source_id:
            db.query(ProductRecord).filter(
                ProductRecord.id.in_(record_ids)
            ).update({ProductRecord.product_id: source_id}, synchronize_session=False)

        # 复活源商品
        if source_id:
            src = db.query(Product).get(source_id)
            if src:
                src.is_active = snap.get("source_is_active", True)
