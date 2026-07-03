"""食材执行器：CRUD（create/update/delete）+ 合并（merge）。

合并复用 IngredientMerger，但 apply 前对受影响行做完整快照
（recipe_ingredients / product_ingredient_links / ingredient_nutrition_mappings /
ingredient_hierarchies + 源食材字段 + 合并记录 id），revert 按快照还原 + 复活源食材 +
删除本次合并记录（IngredientMergeRecord 无 is_active 字段，直接 delete）。

revert 读取 proposal.snapshot / proposal.revert_payload（service._do_apply 已将
ApplyResult.snapshot 落库到 ChangeProposal.snapshot）。
"""
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy import and_, or_
from app.services.proposals.base import ApplyResult
from app.services.proposals.executors._crud_base import CrudExecutorBase
from app.models.nutrition import Ingredient, IngredientNutritionMapping
from app.models.nutrition_data import NutritionData
from app.models.recipe import Recipe, RecipeIngredient
from app.models.product_entity import Product
from app.models.product_ingredient_link import ProductIngredientLink
from app.models.ingredient_hierarchy import IngredientHierarchy
from app.models.ingredient_merge_record import IngredientMergeRecord
from app.services.ingredient_merger import IngredientMerger


class IngredientExecutor(CrudExecutorBase):
    entity_type = "ingredient"
    model_class = Ingredient

    def entity_label(self, db, proposal) -> Optional[str]:
        """create/update/delete 默认查 ingredient.name；merge 显示源→目标。"""
        if proposal.action == "merge":
            p = proposal.payload or {}
            target_id = p.get("target_id")
            source_ids = p.get("source_ids") or []
            names = []
            for sid in source_ids:
                s = db.query(Ingredient).get(sid)
                if s:
                    names.append(s.name)
            tgt = db.query(Ingredient).get(target_id) if target_id else None
            label = ""
            if names:
                label += "源：" + "、".join(names) + " "
            if tgt:
                label += f"目标：「{tgt.name}」"
            return label.strip() or None
        return super().entity_label(db, proposal)

    def validate(self, db, proposal) -> None:
        # 合并校验：源/目标参数完整且源不含目标
        if proposal.action == "merge":
            source_ids = proposal.payload.get("source_ids") or []
            target_id = proposal.payload.get("target_id")
            if not source_ids:
                raise HTTPException(status_code=400, detail="源食材列表不能为空")
            if target_id is None:
                raise HTTPException(status_code=400, detail="缺少目标食材")
            if target_id in source_ids:
                raise HTTPException(status_code=400, detail="目标食材不能同时是源食材")
            return
        # 其余走 CRUD 默认校验
        super().validate(db, proposal)

    def build_snapshot(self, db: Session, proposal) -> dict:
        """覆写：delete 动作额外附带级联商品/层级数量（供审核台展示影响范围）。"""
        snap = super().build_snapshot(db, proposal)
        if proposal.action == "delete":
            eid = proposal.entity_id
            if eid is not None:
                product_count = (
                    db.query(Product)
                    .filter(Product.ingredient_id == eid, Product.is_active.is_(True))
                    .count()
                )
                hierarchy_count = (
                    db.query(IngredientHierarchy)
                    .filter(
                        or_(IngredientHierarchy.parent_id == eid,
                            IngredientHierarchy.child_id == eid),
                    )
                    .count()
                )
                snap["cascade_product_count"] = product_count
                snap["cascade_hierarchy_count"] = hierarchy_count
        return snap

    def preview(self, db, proposal):
        if proposal.action == "merge":
            source_ids = proposal.payload["source_ids"]
            target_id = proposal.payload["target_id"]
            ri = db.query(RecipeIngredient).filter(
                RecipeIngredient.ingredient_id.in_(source_ids)).count()
            pl = db.query(ProductIngredientLink).filter(
                ProductIngredientLink.ingredient_id.in_(source_ids)).count()
            nm = db.query(IngredientNutritionMapping).filter(
                IngredientNutritionMapping.ingredient_id.in_(source_ids)).count()
            hi = db.query(IngredientHierarchy).filter(or_(
                IngredientHierarchy.parent_id.in_(source_ids),
                IngredientHierarchy.child_id.in_(source_ids))).count()
            return {
                "affected_recipe_ingredients": ri,
                "affected_product_links": pl,
                "affected_nutrition_mappings": nm,
                "affected_hierarchies": hi,
                "note": "合并将迁移这些引用到目标食材（含他人菜谱）",
                "target_id": target_id,
            }
        return super().preview(db, proposal)

    def apply(self, db, proposal) -> ApplyResult:
        if proposal.action == "merge":
            return self._apply_merge(db, proposal)
        if proposal.action == "delete":
            return self._apply_delete(db, proposal)
        return super().apply(db, proposal)

    def _apply_merge(self, db, proposal) -> ApplyResult:
        source_ids: List[int] = list(proposal.payload["source_ids"])
        target_id: int = proposal.payload["target_id"]

        # 1. 快照所有受影响行（供 revert）。提前拿到 IngredientMerger 将新建的合并记录 id
        #    （其 _record_merge_history 在 commit 前 flush 不到 id，故 revert 时改为按
        #    (source, target) 条件查询删除）。
        # 批量取可读名（join 一次，避免逐项查询）
        recipe_ids = {r.recipe_id for r in db.query(RecipeIngredient)
                      .filter(RecipeIngredient.ingredient_id.in_(source_ids)).all()}
        product_ids = {l.product_id for l in db.query(ProductIngredientLink)
                       .filter(ProductIngredientLink.ingredient_id.in_(source_ids)).all()}
        nutrition_ids = {m.nutrition_id for m in db.query(IngredientNutritionMapping)
                         .filter(IngredientNutritionMapping.ingredient_id.in_(source_ids)).all()}
        recipe_name_map = {r.id: r.name for r in (
            db.query(Recipe).filter(Recipe.id.in_(recipe_ids)).all()
        )} if recipe_ids else {}
        product_name_map = {p.id: p.name for p in (
            db.query(Product).filter(Product.id.in_(product_ids)).all()
        )} if product_ids else {}
        nutrition_name_map = {n.id: (n.usda_name or n.source or f"#{n.id}") for n in (
            db.query(NutritionData).filter(NutritionData.id.in_(nutrition_ids)).all()
        )} if nutrition_ids else {}

        target = db.query(Ingredient).filter(Ingredient.id == target_id).first()

        snapshot = {
            "target_name": target.name if target else f"#{target_id}",
            "recipe_ingredients": [
                {"id": r.id, "recipe_id": r.recipe_id, "ingredient_id": r.ingredient_id,
                 "recipe_name": recipe_name_map.get(r.recipe_id),
                 "quantity": r.quantity, "quantity_range": r.quantity_range,
                 "unit_id": r.unit_id, "is_optional": r.is_optional, "note": r.note,
                 "original_quantity": r.original_quantity}
                for r in db.query(RecipeIngredient)
                    .filter(RecipeIngredient.ingredient_id.in_(source_ids)).all()
            ],
            "product_links": [
                {"id": l.id, "product_id": l.product_id, "ingredient_id": l.ingredient_id,
                 "product_name": product_name_map.get(l.product_id)}
                for l in db.query(ProductIngredientLink)
                    .filter(ProductIngredientLink.ingredient_id.in_(source_ids)).all()
            ],
            "nutrition_mappings": [
                {"id": m.id, "ingredient_id": m.ingredient_id, "nutrition_id": m.nutrition_id,
                 "nutrition_name": nutrition_name_map.get(m.nutrition_id),
                 "priority": m.priority, "confidence": m.confidence}
                for m in db.query(IngredientNutritionMapping)
                    .filter(IngredientNutritionMapping.ingredient_id.in_(source_ids)).all()
            ],
            "hierarchies": [
                {"id": h.id, "parent_id": h.parent_id, "child_id": h.child_id,
                 "relation_type": h.relation_type, "strength": h.strength}
                for h in db.query(IngredientHierarchy).filter(or_(
                    IngredientHierarchy.parent_id.in_(source_ids),
                    IngredientHierarchy.child_id.in_(source_ids))).all()
            ],
            "sources": [
                {"id": s.id, "is_merged": s.is_merged, "merged_into_id": s.merged_into_id,
                 "aliases": s.aliases, "name": s.name}
                for s in db.query(Ingredient).filter(Ingredient.id.in_(source_ids)).all()
            ],
        }

        # 2. 调现有合并服务（事务内）。IngredientMerger 内部会 db.commit()，
        #    由于走同一 Session，commit 在事务里完成；若外层 revert/apply 需要原子性，
        #    调用方（service）保证异常时不 commit。
        merger = IngredientMerger(db)
        result = merger.merge_ingredients(
            source_ingredient_ids=source_ids,
            target_ingredient_id=target_id,
            merged_by_user_id=proposal.proposer_id,
        )
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message", "合并失败"))

        return ApplyResult(
            snapshot=snapshot,
            revert_payload={"merged": True, "source_ids": source_ids, "target_id": target_id},
            summary=result.get("message", "合并完成"),
        )

    def _apply_delete(self, db, proposal) -> ApplyResult:
        from app.services.proposals.executors._crud_base import _json_safe

        eid = proposal.entity_id
        ing = (
            db.query(Ingredient)
            .filter(Ingredient.id == eid, Ingredient.is_active.is_(True))
            .first()
        )
        if ing is None:
            raise HTTPException(status_code=404, detail=f"食材 {eid} 不存在或已删除")

        # 菜谱引用检查（双层检查之执行器侧）
        recipe_count = (
            db.query(RecipeIngredient)
            .filter(RecipeIngredient.ingredient_id == eid)
            .count()
        )
        if recipe_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"该食材已被 {recipe_count} 个菜谱引用，无法删除。请先移除菜谱中的该食材。",
            )

        # snapshot 级联：活跃商品 id + 相关层级关系 id
        product_ids = [
            p.id for p in db.query(Product).filter(
                Product.ingredient_id == eid, Product.is_active.is_(True)
            ).all()
        ]
        hierarchy_ids = [
            h.id for h in db.query(IngredientHierarchy).filter(
                or_(IngredientHierarchy.parent_id == eid,
                    IngredientHierarchy.child_id == eid)
            ).all()
        ]

        # 主记录全列快照（**必须在置 is_active=False 之前**，对齐基类 _crud_base.py:81 顺序）
        snapshot = {c.name: _json_safe(getattr(ing, c.name)) for c in ing.__table__.columns}
        snapshot["_cascade_product_ids"] = product_ids
        snapshot["_cascade_hierarchy_ids"] = hierarchy_ids
        snapshot["cascade_product_count"] = len(product_ids)
        snapshot["cascade_hierarchy_count"] = len(hierarchy_ids)

        # 级联软删商品
        if product_ids:
            db.query(Product).filter(Product.id.in_(product_ids)).update(
                {"is_active": False}, synchronize_session=False)
        # 级联软删层级关系（parent / child 两向）
        db.query(IngredientHierarchy).filter(
            IngredientHierarchy.parent_id == eid
        ).update({"is_active": False}, synchronize_session=False)
        db.query(IngredientHierarchy).filter(
            IngredientHierarchy.child_id == eid
        ).update({"is_active": False}, synchronize_session=False)

        # 软删食材
        ing.is_active = False

        return ApplyResult(
            snapshot=snapshot,
            revert_payload={"restore_active": True,
                            "cascade_product_ids": product_ids,
                            "cascade_hierarchy_ids": hierarchy_ids},
            summary=f"已软删食材 {eid}（级联 {len(product_ids)} 商品 / {len(hierarchy_ids)} 层级）",
        )

    def _revert_delete(self, db, proposal) -> None:
        rp = proposal.revert_payload or {}
        eid = proposal.entity_id
        ing = db.query(Ingredient).get(eid) if eid else None
        if ing is not None:
            ing.is_active = True
        # 反级联：复活商品
        product_ids = rp.get("cascade_product_ids") or []
        if product_ids:
            db.query(Product).filter(Product.id.in_(product_ids)).update(
                {"is_active": True}, synchronize_session=False)
        # 反级联：复活层级关系
        hierarchy_ids = rp.get("cascade_hierarchy_ids") or []
        if hierarchy_ids:
            db.query(IngredientHierarchy).filter(
                IngredientHierarchy.id.in_(hierarchy_ids)
            ).update({"is_active": True}, synchronize_session=False)

    def revert(self, db, proposal) -> None:
        if proposal.action == "merge":
            self._revert_merge(db, proposal)
            return
        if proposal.action == "delete":
            self._revert_delete(db, proposal)
            return
        super().revert(db, proposal)

    def _revert_merge(self, db, proposal) -> None:
        snap = proposal.snapshot or {}
        rp = proposal.revert_payload or {}
        source_ids = rp.get("source_ids", [])
        target_id = rp.get("target_id")

        # 1. 还原 recipe_ingredients：被改 ingredient_id 的恢复，被删的重新插入
        ri_cols = {c.name for c in RecipeIngredient.__table__.columns}
        existing_ri = {r.id for r in db.query(RecipeIngredient).all()}
        for item in snap.get("recipe_ingredients", []):
            if item["id"] in existing_ri:
                r = db.query(RecipeIngredient).get(item["id"])
                if r is not None:
                    r.ingredient_id = item["ingredient_id"]
                    r.quantity = item["quantity"]
                    r.quantity_range = item["quantity_range"]
                    r.unit_id = item["unit_id"]
                    r.is_optional = item["is_optional"]
                    r.note = item["note"]
                    r.original_quantity = item["original_quantity"]
            else:
                db.add(RecipeIngredient(**{k: v for k, v in item.items() if k in ri_cols}))
        # 合并过程中 quantity 可能被追加到目标行（"100 + 200"），那部分无法精确还原，
        # revert 依赖快照行重建源行 + 目标行数量变更不在快照内（仅源行快照）——接受此局限。

        # 2. 还原 product_links：被删的重新插入（被改 ingredient_id 的恢复）
        pl_cols = {c.name for c in ProductIngredientLink.__table__.columns}
        existing_pl = {l.id for l in db.query(ProductIngredientLink).all()}
        for item in snap.get("product_links", []):
            if item["id"] in existing_pl:
                l = db.query(ProductIngredientLink).get(item["id"])
                if l is not None:
                    l.ingredient_id = item["ingredient_id"]
            else:
                db.add(ProductIngredientLink(**{k: v for k, v in item.items() if k in pl_cols}))

        # 3. 还原 nutrition_mappings
        nm_cols = {c.name for c in IngredientNutritionMapping.__table__.columns}
        existing_nm = {m.id for m in db.query(IngredientNutritionMapping).all()}
        for item in snap.get("nutrition_mappings", []):
            if item["id"] in existing_nm:
                m = db.query(IngredientNutritionMapping).get(item["id"])
                if m is not None:
                    m.ingredient_id = item["ingredient_id"]
                    m.priority = item["priority"]
                    m.confidence = item["confidence"]
            else:
                db.add(IngredientNutritionMapping(**{k: v for k, v in item.items() if k in nm_cols}))

        # 4. 还原 hierarchies
        existing_h = {h.id for h in db.query(IngredientHierarchy).all()}
        for item in snap.get("hierarchies", []):
            if item["id"] in existing_h:
                h = db.query(IngredientHierarchy).get(item["id"])
                if h is not None:
                    h.parent_id = item["parent_id"]
                    h.child_id = item["child_id"]
                    h.relation_type = item["relation_type"]
                    h.strength = item["strength"]
            else:
                db.add(IngredientHierarchy(**item))

        # 5. 复活源食材：还原 is_merged / merged_into_id / aliases / name
        for s in snap.get("sources", []):
            ing = db.query(Ingredient).get(s["id"])
            if ing is not None:
                ing.is_merged = s["is_merged"]
                ing.merged_into_id = s["merged_into_id"]
                ing.aliases = s["aliases"]
                # name 在合并时未被改（merger 只动 aliases），无需还原；保险起见恢复
                ing.name = s["name"]

        # 6. 删除本次合并记录（IngredientMergeRecord 无 is_active，直接 delete）
        if source_ids and target_id is not None:
            db.query(IngredientMergeRecord).filter(
                IngredientMergeRecord.source_ingredient_id.in_(source_ids),
                IngredientMergeRecord.target_ingredient_id == target_id,
            ).delete(synchronize_session=False)
