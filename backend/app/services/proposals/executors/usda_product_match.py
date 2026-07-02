"""USDA 商品匹配执行器：覆盖 Product.custom_nutrition_data。

apply 前 snapshot 旧 custom_nutrition_data → 调 match_product → revert_payload。
revert 还原旧值（JSON 列，简单）。

entity_id = product_id；payload 含 fdc_id。
"""
from typing import Optional
from fastapi import HTTPException

from app.services.proposals.base import ProposalExecutor, ApplyResult
from app.services.proposals.executors._crud_base import _json_safe
from app.models.product_entity import Product


class UsdaProductMatchExecutor(ProposalExecutor):
    entity_type = "usda_product_match"

    def validate(self, db, proposal) -> None:
        product_id = proposal.entity_id
        fdc_id = (proposal.payload or {}).get("fdc_id")
        if product_id is None or fdc_id is None:
            raise HTTPException(status_code=400, detail="payload 缺少 fdc_id / entity_id")
        if db.query(Product).filter(Product.id == product_id,
                                    Product.is_active.is_(True)).first() is None:
            raise HTTPException(status_code=404, detail="商品不存在")

    def build_snapshot(self, db, proposal) -> dict:
        """提交时预填旧 custom_nutrition_data。"""
        product_id = proposal.entity_id
        if product_id is None:
            return {}
        prod = db.query(Product).get(product_id)
        old_cnd = prod.custom_nutrition_data if prod else None
        return {"old_custom_nutrition_data": _json_safe(old_cnd)}

    def preview(self, db, proposal) -> dict:
        product_id = proposal.entity_id
        prod = db.query(Product).get(product_id) if product_id else None
        has = bool(prod and prod.custom_nutrition_data)
        return {"product_id": product_id, "has_custom_nutrition": has}

    def apply(self, db, proposal) -> ApplyResult:
        product_id = proposal.entity_id
        fdc_id = (proposal.payload or {}).get("fdc_id")
        prod = db.query(Product).get(product_id)
        old_cnd = prod.custom_nutrition_data  # 旧值（可能 None）
        snapshot = {"old_custom_nutrition_data": _json_safe(old_cnd)}
        from app.services.usda.matcher import match_product
        match_product(db, product_id, fdc_id)
        return ApplyResult(
            snapshot=snapshot,
            revert_payload={"product_id": product_id},
            summary=f"USDA 匹配商品 {product_id} → fdc {fdc_id}",
        )

    def revert(self, db, proposal) -> None:
        rp = proposal.revert_payload or {}
        snap = proposal.snapshot or {}
        product_id = rp.get("product_id")
        old_cnd = snap.get("old_custom_nutrition_data")
        if product_id is not None:
            prod = db.query(Product).get(product_id)
            if prod is not None:
                prod.custom_nutrition_data = old_cnd

    def entity_label(self, db, proposal) -> Optional[str]:
        product_id = proposal.entity_id
        prod = db.query(Product).get(product_id) if product_id else None
        return f"商品「{prod.name}」USDA 匹配" if prod else None
