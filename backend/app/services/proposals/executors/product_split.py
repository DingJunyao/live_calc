"""商品拆分为原料执行器。

把商品从原原料中拆出，以商品名创建新原料，迁移营养数据（商品自定义+原料营养合并），
商品关联到新原料，清空商品自定义营养数据。

payload: { new_name: str | None } — 可选新原料名称（同名冲突时必填）
entity_id: product_id
"""
from typing import Optional

from fastapi import HTTPException

from app.services.proposals.base import ApplyResult, ProposalExecutor


class ProductSplitExecutor(ProposalExecutor):
    entity_type = "product_split"

    def entity_label(self, db, proposal) -> Optional[str]:
        from app.models.product_entity import Product
        eid = proposal.entity_id
        if eid is None:
            return None
        p = db.query(Product).get(eid)
        return f"商品「{p.name}」" if p else None

    def build_snapshot(self, db, proposal) -> dict:
        from app.models.product_entity import Product
        eid = proposal.entity_id
        if eid is None:
            return {}
        p = db.query(Product).get(eid)
        if p is None:
            return {}
        new_name = (proposal.payload or {}).get("new_name") or p.name
        return {
            "product_name": p.name,
            "current_ingredient_name": p.ingredient.name if p.ingredient else "?",
            "new_ingredient_name": new_name,
        }

    def validate(self, db, proposal) -> None:
        from app.models.product_entity import Product
        eid = proposal.entity_id
        if eid is None:
            raise HTTPException(status_code=400, detail="需要商品 ID")
        p = db.query(Product).filter(
            Product.id == eid, Product.is_active == True
        ).first()
        if p is None:
            raise HTTPException(status_code=404, detail="商品不存在或已删除")
        if not p.ingredient_id:
            raise HTTPException(status_code=400, detail="商品未关联原料")
        # 唯一商品检查（端点也要查，执行器再查一次防审核期间变化）
        cnt = db.query(Product).filter(
            Product.ingredient_id == p.ingredient_id,
            Product.is_active == True,
            Product.id != eid,
        ).count()
        if cnt == 0:
            raise HTTPException(
                status_code=400,
                detail="该商品是当前原料的唯一商品，无法拆分。请先为该原料添加其他商品。"
            )

    def preview(self, db, proposal) -> dict:
        from app.models.product_entity import Product
        eid = proposal.entity_id
        p = db.query(Product).get(eid) if eid else None
        cur_ing = p.ingredient if p and p.ingredient else None
        return {
            "product_name": p.name if p else "?",
            "current_ingredient": cur_ing.name if cur_ing else "?",
            "note": "将根据商品名创建新原料，迁移营养数据",
        }

    def apply(self, db, proposal) -> ApplyResult:
        from app.models.product_entity import Product
        from app.models.nutrition import Ingredient
        from app.models.nutrition_data import NutritionData

        eid = proposal.entity_id
        new_name = (proposal.payload or {}).get("new_name")
        p = db.query(Product).filter(
            Product.id == eid, Product.is_active == True
        ).first()
        if p is None:
            raise HTTPException(status_code=404, detail="商品不存在或已删除")

        current_ingredient = p.ingredient
        if not current_ingredient:
            raise HTTPException(status_code=400, detail="商品未关联原料")

        # 快照当前状态（供 revert）
        snapshot = {
            "product_ingredient_id": p.ingredient_id,
            "product_custom_nutrition_data": p.custom_nutrition_data,
            "product_custom_nutrition_source": p.custom_nutrition_source,
        }

        # 确定名称
        ingredient_name = (new_name or p.name).strip()
        if not ingredient_name:
            raise HTTPException(status_code=400, detail="原料名称不能为空")

        # 检查同名
        existing = db.query(Ingredient).filter(
            Ingredient.name == ingredient_name,
            Ingredient.is_active == True,
        ).first()
        if existing:
            if existing.id == current_ingredient.id:
                raise HTTPException(
                    status_code=409,
                    detail="名称与当前关联原料同名，请指定不同的新原料名称。"
                )
            raise HTTPException(
                status_code=409,
                detail=f"原料「{ingredient_name}」已存在（ID: {existing.id}），请指定不同的名称。"
            )

        # 获取营养数据合并
        product_nutrition = p.custom_nutrition_data or {}
        ingredient_nutrition = self._get_ingredient_nutrition(db, current_ingredient)
        merged = self._merge_nutrition(product_nutrition, ingredient_nutrition)

        # 默认单位（斤）
        from app.models.unit import Unit
        unit_id = None
        jin_unit = db.query(Unit).filter(Unit.abbreviation == "斤").first()
        if jin_unit:
            unit_id = jin_unit.id

        # 创建新原料
        new_ingredient = Ingredient(
            name=ingredient_name,
            aliases=[],
            default_unit_id=unit_id,
            created_by=proposal.proposer_id,
            updated_by=proposal.proposer_id,
        )
        db.add(new_ingredient)
        db.flush()
        snapshot["new_ingredient_id"] = new_ingredient.id

        # 将合并营养数据写入新原料
        has_nutrition = bool(
            merged.get("core_nutrients") or merged.get("all_nutrients")
        )
        if has_nutrition:
            nr = NutritionData(
                ingredient_id=new_ingredient.id,
                source="custom",
                nutrients=merged,
                reference_amount=100.0,
                reference_unit="g",
                match_confidence=1.0,
                is_verified=True,
                created_by=proposal.proposer_id,
                updated_by=proposal.proposer_id,
            )
            db.add(nr)
            db.flush()

        # 更新商品：关联新原料，清空自定义营养
        p.ingredient_id = new_ingredient.id
        p.custom_nutrition_data = None
        p.custom_nutrition_source = None

        return ApplyResult(
            snapshot=snapshot,
            revert_payload={"new_ingredient_id": new_ingredient.id},
            summary=f"已拆分为新原料「{ingredient_name}」",
        )

    def revert(self, db, proposal) -> None:
        from app.models.product_entity import Product
        from app.models.nutrition import Ingredient

        snap = proposal.snapshot or {}
        eid = proposal.entity_id

        # 还原商品
        p = db.query(Product).get(eid) if eid else None
        if p:
            p.ingredient_id = snap.get("product_ingredient_id", p.ingredient_id)
            p.custom_nutrition_data = snap.get("product_custom_nutrition_data")
            p.custom_nutrition_source = snap.get("product_custom_nutrition_source")

        # 软删新原料
        new_ing_id = snap.get("new_ingredient_id")
        if new_ing_id:
            ing = db.query(Ingredient).get(new_ing_id)
            if ing:
                ing.is_active = False

    # ── 辅助方法 ──

    def _get_ingredient_nutrition(self, db, ingredient) -> dict:
        from app.models.nutrition_data import NutritionData
        records = (
            db.query(NutritionData)
            .filter(NutritionData.ingredient_id == ingredient.id)
            .order_by(NutritionData.is_verified.desc(), NutritionData.id.desc())
            .all()
        )
        if not records:
            return {}
        return records[0].nutrients or {}

    def _merge_nutrition(self, product_nut: dict, ingredient_nut: dict) -> dict:
        """合并商品↔原料营养，商品优于原料。"""
        result = {}
        for key in ("core_nutrients", "all_nutrients", "nutrient_details"):
            merged = {}
            ing_part = ingredient_nut.get(key, {}) if isinstance(ingredient_nut, dict) else {}
            prod_part = product_nut.get(key, {}) if isinstance(product_nut, dict) else {}
            merged.update(ing_part)
            merged.update(prod_part)
            if merged:
                result[key] = merged
        return result
