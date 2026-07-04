"""商品营养数据执行器：覆盖 Product.custom_nutrition_data + custom_nutrition_source。

apply 前 snapshot 旧 custom_nutrition_data + source → 写 payload 的值 → revert_payload。
revert 还原旧值。和 UsdaProductMatchExecutor 同构（都写 custom_nutrition_data），
但本执行器写用户编辑的 structured_nutrients（payload），不调 matcher。

entity_id = product_id；payload 含 custom_nutrition_data / custom_nutrition_source / updated_by。
"""
from typing import Optional
from fastapi import HTTPException

from app.services.proposals.base import ProposalExecutor, ApplyResult
from app.services.proposals.executors._crud_base import _json_safe
from app.models.product_entity import Product


class ProductNutritionExecutor(ProposalExecutor):
    entity_type = "product_nutrition"

    def validate(self, db, proposal) -> None:
        product_id = proposal.entity_id
        if product_id is None:
            raise HTTPException(status_code=400, detail="需 entity_id")
        if db.query(Product).filter(Product.id == product_id,
                                    Product.is_active.is_(True)).first() is None:
            raise HTTPException(status_code=404, detail="商品不存在")

    def build_snapshot(self, db, proposal) -> dict:
        """提交时预填旧 custom_nutrition_data。"""
        product_id = proposal.entity_id
        if product_id is None:
            return {}
        prod = db.query(Product).get(product_id)
        if prod is None:
            return {}
        return {
            "old_custom_nutrition_data": _json_safe(prod.custom_nutrition_data),
            "old_custom_nutrition_source": _json_safe(prod.custom_nutrition_source),
        }

    def preview(self, db, proposal) -> dict:
        product_id = proposal.entity_id
        prod = db.query(Product).get(product_id) if product_id else None
        return {"product_id": product_id,
                "has_custom_nutrition": bool(prod and prod.custom_nutrition_data)}

    def apply(self, db, proposal) -> ApplyResult:
        product_id = proposal.entity_id
        prod = db.query(Product).get(product_id)
        old_cnd = prod.custom_nutrition_data
        old_source = prod.custom_nutrition_source
        snapshot = {
            "old_custom_nutrition_data": _json_safe(old_cnd),
            "old_custom_nutrition_source": _json_safe(old_source),
        }
        p = proposal.payload or {}
        prod.custom_nutrition_data = p.get("custom_nutrition_data")
        prod.custom_nutrition_source = p.get("custom_nutrition_source")
        if "updated_by" in p:
            prod.updated_by = p["updated_by"]
        return ApplyResult(
            snapshot=snapshot,
            revert_payload={"product_id": product_id},
            summary=f"商品 {product_id} 营养数据已更新",
        )

    def revert(self, db, proposal) -> None:
        snap = proposal.snapshot or {}
        product_id = proposal.entity_id
        prod = db.query(Product).get(product_id) if product_id else None
        if prod is not None:
            prod.custom_nutrition_data = snap.get("old_custom_nutrition_data")
            prod.custom_nutrition_source = snap.get("old_custom_nutrition_source")

    def entity_label(self, db, proposal) -> Optional[str]:
        product_id = proposal.entity_id
        prod = db.query(Product).get(product_id) if product_id else None
        return f"商品「{prod.name}」营养数据" if prod else None
