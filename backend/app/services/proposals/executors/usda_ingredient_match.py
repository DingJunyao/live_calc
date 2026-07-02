"""USDA 原料匹配执行器：替换语义（清空旧 NutritionData + 写 USDA 的）。

apply 前 snapshot 该原料所有旧 NutritionData（全字段）→ 调 match_ingredient →
revert_payload（旧数据 + fdc_id）。revert 删 USDA 新行（usda_id=fdc_id）+ 插旧行（新 id，
NutritionData 是叶表无外键引用，id 变化安全）。

entity_id = ingredient_id；payload 含 fdc_id。
"""
from datetime import datetime
from typing import Optional
from fastapi import HTTPException

from app.services.proposals.base import ProposalExecutor, ApplyResult
from app.services.proposals.executors._crud_base import _json_safe
from app.models.nutrition import Ingredient
from app.models.nutrition_data import NutritionData

# AuditMixin 的时间戳列：snapshot 经 _json_safe 转成 isoformat 字符串，
# 重新插入 NutritionData 整行前必须转回 datetime（SQLite DateTime 列拒收字符串）。
_TIMESTAMP_COLS = ("created_at", "updated_at", "verified_at", "edited_at")


def _restore_row(row: dict) -> dict:
    """把 snapshot 行还原成可插入 ORM 的 dict：去掉 id，时间戳字符串转回 datetime。"""
    data = dict(row)
    data.pop("id", None)
    for col in _TIMESTAMP_COLS:
        v = data.get(col)
        if isinstance(v, str):
            try:
                data[col] = datetime.fromisoformat(v)
            except ValueError:
                data[col] = None
    return data


class UsdaIngredientMatchExecutor(ProposalExecutor):
    entity_type = "usda_ingredient_match"

    def validate(self, db, proposal) -> None:
        ingredient_id = proposal.entity_id
        fdc_id = (proposal.payload or {}).get("fdc_id")
        if ingredient_id is None or fdc_id is None:
            raise HTTPException(status_code=400, detail="payload 缺少 fdc_id / entity_id")
        if db.query(Ingredient).filter(Ingredient.id == ingredient_id,
                                       Ingredient.is_active.is_(True)).first() is None:
            raise HTTPException(status_code=404, detail="原料不存在")

    def build_snapshot(self, db, proposal) -> dict:
        """提交时预填旧 NutritionData 全行。"""
        ingredient_id = proposal.entity_id
        if ingredient_id is None:
            return {"old_nutrition_data": []}
        old_rows = db.query(NutritionData).filter(
            NutritionData.ingredient_id == ingredient_id).all()
        return {
            "old_nutrition_data": [
                {c.name: _json_safe(getattr(r, c.name)) for c in r.__table__.columns}
                for r in old_rows
            ],
        }

    def preview(self, db, proposal) -> dict:
        ingredient_id = proposal.entity_id
        existing = db.query(NutritionData).filter(
            NutritionData.ingredient_id == ingredient_id).count()
        return {"ingredient_id": ingredient_id, "existing_nutrition_rows": existing,
                "note": "将清空现有营养数据并写入 USDA 匹配数据"}

    def apply(self, db, proposal) -> ApplyResult:
        ingredient_id = proposal.entity_id
        fdc_id = (proposal.payload or {}).get("fdc_id")
        # snapshot 旧 NutritionData（清空前）
        old_rows = db.query(NutritionData).filter(
            NutritionData.ingredient_id == ingredient_id).all()
        snapshot = {
            "old_nutrition_data": [
                {c.name: _json_safe(getattr(r, c.name)) for c in r.__table__.columns}
                for r in old_rows
            ],
        }
        # 调 matcher（清空+写新，flush）
        from app.services.usda.matcher import match_ingredient
        match_ingredient(db, ingredient_id, fdc_id)
        return ApplyResult(
            snapshot=snapshot,
            revert_payload={"ingredient_id": ingredient_id, "fdc_id": str(fdc_id)},
            summary=f"USDA 匹配原料 {ingredient_id} → fdc {fdc_id}",
        )

    def revert(self, db, proposal) -> None:
        rp = proposal.revert_payload or {}
        snap = proposal.snapshot or {}
        ingredient_id = rp.get("ingredient_id")
        fdc_id = rp.get("fdc_id")
        # 删 USDA 新行（match_ingredient 写的，usda_id=fdc_id）
        if ingredient_id is not None and fdc_id is not None:
            db.query(NutritionData).filter(
                NutritionData.ingredient_id == ingredient_id,
                NutritionData.usda_id == fdc_id,
            ).delete(synchronize_session=False)
        # 插旧行（snapshot，新 id）
        for row in snap.get("old_nutrition_data", []):
            db.add(NutritionData(**_restore_row(row)))

    def entity_label(self, db, proposal) -> Optional[str]:
        ingredient_id = proposal.entity_id
        ing = db.query(Ingredient).get(ingredient_id) if ingredient_id else None
        return f"原料「{ing.name}」USDA 匹配" if ing else None
