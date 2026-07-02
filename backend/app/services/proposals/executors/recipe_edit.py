"""菜谱编辑执行器：已发布菜谱的修改走提议审核。

snapshot 在 apply/submit 时都存入 ``old_ingredients``（删除/替换前的旧食材列表，
含 ``ingredient_name``/``unit_name`` 等可读冗余名），供审核台双栏 diff 与
revert 食材回滚。复用基类 ``_json_safe``（Decimal→str 无损，与 CRUD 执行器一致）。
"""
from typing import Optional

from fastapi import HTTPException

from app.models.recipe import Recipe, RecipeIngredient
from app.models.nutrition import Ingredient
from app.models.unit import Unit
from app.services.proposals.base import ProposalExecutor, ApplyResult
from app.services.proposals.executors._crud_base import _json_safe
from sqlalchemy import Date, DateTime
from sqlalchemy.orm import load_only


class RecipeEditExecutor(ProposalExecutor):
    entity_type = "recipe_edit"

    def entity_label(self, db, proposal) -> Optional[str]:
        eid = proposal.entity_id
        if eid is None:
            return None
        r = db.query(Recipe).get(eid)
        return f"菜谱「{r.name}」" if r else None

    def validate(self, db, proposal):
        r = db.query(Recipe).filter(Recipe.id == proposal.entity_id).first()
        if r is None:
            raise HTTPException(status_code=404, detail="菜谱不存在")

    def preview(self, db, proposal):
        r = db.query(Recipe).filter(Recipe.id == proposal.entity_id).first()
        return {"recipe_id": proposal.entity_id, "name": r.name if r else None,
                "changes": list(proposal.payload.get("update_data", {}).keys())}

    # ---- 旧食材快照：apply 前 / submit 预填 共用 ----
    def _snapshot_old_ingredients(self, db, recipe_id) -> list:
        rows = db.query(RecipeIngredient).filter(
            RecipeIngredient.recipe_id == recipe_id
        ).all()
        # 批量取相关原料名 / 单位名，避免逐行查询风暴
        ing_ids = {r.ingredient_id for r in rows if r.ingredient_id}
        unit_ids = {r.unit_id for r in rows if r.unit_id}
        ing_map = {i.id: i.name for i in (
            db.query(Ingredient).filter(Ingredient.id.in_(ing_ids)).all()
        )} if ing_ids else {}
        unit_map = {u.id: u.name for u in (
            db.query(Unit).filter(Unit.id.in_(unit_ids)).all()
        )} if unit_ids else {}
        out = []
        for ri in rows:
            out.append({
                "id": ri.id,
                "ingredient_id": ri.ingredient_id,
                "ingredient_name": ing_map.get(ri.ingredient_id),
                "quantity": ri.quantity,
                "quantity_range": ri.quantity_range,
                "unit_id": ri.unit_id,
                "unit_name": unit_map.get(ri.unit_id),
                "is_optional": ri.is_optional,
                "note": ri.note,
                "original_quantity": ri.original_quantity,
            })
        return out

    def _snapshot_scalar_cols(self, recipe) -> dict:
        """菜谱标量列快照（apply/submit 共用，与 _snapshot_old_ingredients 配对）。"""
        return {c.name: _json_safe(getattr(recipe, c.name))
                for c in recipe.__table__.columns}

    def build_snapshot(self, db, proposal) -> dict:
        """submit 时预填 before（供 pending 审核看旧食材；apply 时被覆盖）。"""
        recipe_id = proposal.entity_id
        if recipe_id is None:
            return {}
        recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
        if recipe is None:
            return {}
        snap = self._snapshot_scalar_cols(recipe)
        snap["old_ingredients"] = self._snapshot_old_ingredients(db, recipe_id)
        return snap

    def apply(self, db, proposal) -> ApplyResult:
        recipe_id = proposal.entity_id
        recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
        if recipe is None:
            raise HTTPException(status_code=404, detail="菜谱不存在")

        update_data = proposal.payload.get("update_data", {})

        # 标量列快照（apply 前最新值）
        snapshot = self._snapshot_scalar_cols(recipe)
        # 旧食材快照（在替换前抓全量；审核台 diff + revert 回滚 都用它）
        snapshot["old_ingredients"] = self._snapshot_old_ingredients(db, recipe_id)

        model_cols = {c.name for c in Recipe.__table__.columns}
        skip_fields = {"id", "is_public", "user_id", "source", "created_at", "updated_at",
                       "created_by", "updated_by", "is_active", "ingredients"}

        # 全量替换食材
        if "ingredients" in update_data and update_data["ingredients"] is not None:
            db.query(RecipeIngredient).filter(
                RecipeIngredient.recipe_id == recipe_id
            ).delete(synchronize_session=False)
            for ing_data in update_data["ingredients"]:
                ing = db.query(Ingredient).options(
                    load_only(Ingredient.id, Ingredient.name, Ingredient.is_active)
                ).filter(Ingredient.name == ing_data.get("ingredient_name")).first()
                if ing:
                    db.add(RecipeIngredient(
                        recipe_id=recipe_id,
                        ingredient_id=ing.id,
                        quantity=ing_data.get("quantity"),
                        quantity_range=ing_data.get("quantity_range"),
                        unit_id=ing_data.get("unit_id"),
                        is_optional=ing_data.get("is_optional", False),
                        note=ing_data.get("note"),
                        original_quantity=ing_data.get("original_quantity"),
                    ))

        # 更新所有匹配模型列的标量字段
        for k, v in update_data.items():
            if k in model_cols and k not in skip_fields and v is not None:
                setattr(recipe, k, v)

        db.flush()
        return ApplyResult(snapshot=snapshot, revert_payload=snapshot,
                           summary=f"编辑菜谱 {recipe.name}")

    def revert(self, db, proposal):
        recipe_id = proposal.entity_id
        recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
        snap = proposal.snapshot or {}

        # 标量字段还原（跳过 DateTime/Date 列：_json_safe 把它们转成了 isoformat
        # 字符串，SQLite DateTime 拒收 str；且审计时间戳不应回滚）
        datetime_cols = {c.name for c in Recipe.__table__.columns
                         if isinstance(c.type, (DateTime, Date))}
        if recipe is not None:
            for k, v in snap.items():
                if k == "old_ingredients" or k in datetime_cols:
                    continue
                if hasattr(recipe, k):
                    setattr(recipe, k, v)

        # 食材回滚：删当前 + 按快照重建旧食材（不指定 id，让自增，避免主键冲突）
        old_ings = snap.get("old_ingredients")
        if old_ings is not None and recipe_id is not None:
            db.query(RecipeIngredient).filter(
                RecipeIngredient.recipe_id == recipe_id
            ).delete(synchronize_session=False)
            for ing_data in old_ings:
                db.add(RecipeIngredient(
                    recipe_id=recipe_id,
                    ingredient_id=ing_data.get("ingredient_id"),
                    quantity=ing_data.get("quantity"),
                    quantity_range=ing_data.get("quantity_range"),
                    unit_id=ing_data.get("unit_id"),
                    is_optional=ing_data.get("is_optional", False),
                    note=ing_data.get("note"),
                    original_quantity=ing_data.get("original_quantity"),
                ))
            db.flush()
