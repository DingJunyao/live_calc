"""商品执行器：CRUD + 软删（delete 级联 ProductRecord，revert 反级联复活）。

继承 CrudExecutorBase：update 吃基类 setattr；delete 覆写——
唯一商品检查（原料的唯一活跃商品拒删）+ 软删 Product + 级联软删其 ProductRecord +
snapshot；revert 按 snapshot 反级联复活 Product + ProductRecord。

payload 期望（update）：商品基本信息字段（name/brand/barcode/ingredient_id/tags/aliases/updated_by）。
entity_id：Product.id。
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.proposals.base import ApplyResult
from app.services.proposals.executors._crud_base import CrudExecutorBase, _json_safe
from app.models.product_entity import Product
from app.models.product import ProductRecord


class ProductExecutor(CrudExecutorBase):
    entity_type = "product"
    model_class = Product

    def validate(self, db: Session, proposal) -> None:
        action = proposal.action
        if action == "create":
            return  # 商品 create 不在本次范围
        eid = proposal.entity_id
        if eid is None:
            raise HTTPException(status_code=400, detail="update/delete 需 entity_id")
        obj = (
            db.query(Product)
            .filter(Product.id == eid, Product.is_active.is_(True))
            .first()
        )
        if obj is None:
            raise HTTPException(status_code=404, detail=f"商品 {eid} 不存在或已删除")

    def apply(self, db: Session, proposal) -> ApplyResult:
        if proposal.action == "delete":
            return self._apply_delete(db, proposal)
        return super().apply(db, proposal)

    def _apply_delete(self, db: Session, proposal) -> ApplyResult:
        eid = proposal.entity_id
        obj = (
            db.query(Product)
            .filter(Product.id == eid, Product.is_active.is_(True))
            .first()
        )
        if obj is None:
            raise HTTPException(status_code=404, detail=f"商品 {eid} 不存在或已删除")

        # 唯一商品检查：原料的唯一活跃商品不能删（双层检查之执行器侧）
        sibling_count = (
            db.query(Product)
            .filter(
                Product.ingredient_id == obj.ingredient_id,
                Product.is_active.is_(True),
                Product.id != eid,
            )
            .count()
        )
        if sibling_count == 0:
            raise HTTPException(
                status_code=400,
                detail=f"「{obj.name}」是其所属原料的唯一商品，无法删除。请先为该原料添加其他商品后再删除。",
            )

        # snapshot 级联 ProductRecord id（供 revert 复活）
        record_ids = [
            r.id
            for r in db.query(ProductRecord)
            .filter(ProductRecord.product_id == eid)
            .all()
        ]

        # 主记录全列快照（**必须在置 is_active=False 之前**，对齐基类 _crud_base.py:81 顺序）
        snapshot = {c.name: _json_safe(getattr(obj, c.name)) for c in obj.__table__.columns}
        snapshot["_cascade_record_ids"] = record_ids

        # 软删 Product + 级联软删 ProductRecord
        obj.is_active = False
        if record_ids:
            db.query(ProductRecord).filter(
                ProductRecord.product_id == eid
            ).update({"is_active": False}, synchronize_session=False)

        return ApplyResult(
            snapshot=snapshot,
            revert_payload={"restore_active": True, "cascade_record_ids": record_ids},
            summary=f"已软删商品 {eid}（级联 {len(record_ids)} 条价格记录）",
        )

    def revert(self, db: Session, proposal) -> None:
        if proposal.action != "delete":
            return super().revert(db, proposal)
        rp = proposal.revert_payload or {}
        eid = proposal.entity_id
        obj = db.query(Product).get(eid) if eid else None
        if obj is not None:
            obj.is_active = True
        # 反级联：复活 ProductRecord
        cascade_ids = rp.get("cascade_record_ids") or []
        if cascade_ids:
            db.query(ProductRecord).filter(
                ProductRecord.id.in_(cascade_ids)
            ).update({"is_active": True}, synchronize_session=False)
