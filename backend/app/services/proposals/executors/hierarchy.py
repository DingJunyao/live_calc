"""食材层级关系执行器：CRUD。

payload（create）：{parent_id, child_id, relation_type, strength?}
update：{strength?} 等；delete：软删。
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.services.proposals.executors._crud_base import CrudExecutorBase
from app.models.ingredient_hierarchy import IngredientHierarchy


class HierarchyExecutor(CrudExecutorBase):
    entity_type = "hierarchy"
    model_class = IngredientHierarchy

    def build_snapshot(self, db: Session, proposal) -> dict:
        """提交时预填 before + 冗余 parent/child 名称供前端层级渲染器使用。"""
        from app.models.nutrition import Ingredient
        snap = super().build_snapshot(db, proposal)
        for fld in ('parent_id', 'child_id'):
            val = snap.get(fld)
            if val is not None:
                ing = db.query(Ingredient).get(val)
                if ing:
                    snap[f'_{fld}_name'] = ing.name
        return snap

    def entity_label(self, db, proposal) -> Optional[str]:
        """entity_id 是层级关系 id，查 parent/child ingredient name。"""
        from app.models.nutrition import Ingredient
        eid = proposal.entity_id
        if eid is None:
            # create：payload 可能含 parent_id/child_id
            p = proposal.payload or {}
            pid, cid = p.get("parent_id"), p.get("child_id")
        else:
            h = db.query(IngredientHierarchy).get(eid)
            pid = h.parent_id if h else None
            cid = h.child_id if h else None
        parts = []
        if pid:
            pi = db.query(Ingredient).get(pid)
            if pi:
                parts.append(f"父：「{pi.name}」")
        if cid:
            ci = db.query(Ingredient).get(cid)
            if ci:
                parts.append(f"子：「{ci.name}」")
        return " ".join(parts) if parts else None
