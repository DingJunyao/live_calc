"""菜谱发布执行器：apply 置 is_public=True，revert 置回 False。"""
from typing import Optional
from fastapi import HTTPException
from app.services.proposals.base import ProposalExecutor, ApplyResult
from app.models.recipe import Recipe


class RecipePublishExecutor(ProposalExecutor):
    entity_type = "recipe"

    def entity_label(self, db, proposal) -> Optional[str]:
        """entity_id 是 recipe.id，查 recipe.name。"""
        eid = proposal.entity_id
        if eid is None:
            return None
        r = db.query(Recipe).get(eid)
        return f"菜谱「{r.name}」" if r else None

    def validate(self, db, proposal):
        r = db.query(Recipe).filter(Recipe.id == proposal.entity_id).first()
        if r is None:
            raise HTTPException(status_code=404, detail="菜谱不存在")
        if getattr(r, "is_public", False):
            raise HTTPException(status_code=400, detail="菜谱已发布")

    def preview(self, db, proposal):
        r = db.query(Recipe).filter(Recipe.id == proposal.entity_id).first()
        return {"recipe_id": proposal.entity_id, "name": r.name if r else None,
                "will_publish": True}

    def apply(self, db, proposal) -> ApplyResult:
        r = db.query(Recipe).filter(Recipe.id == proposal.entity_id).first()
        if r is None:
            raise HTTPException(status_code=404, detail="菜谱不存在")
        snapshot = {"is_public": bool(getattr(r, "is_public", False))}
        r.is_public = True
        return ApplyResult(snapshot=snapshot,
                           revert_payload={"set_public": snapshot["is_public"]},
                           summary=f"菜谱 {r.name} 已发布")

    def revert(self, db, proposal):
        r = db.query(Recipe).filter(Recipe.id == proposal.entity_id).first()
        if r is not None:
            r.is_public = bool((proposal.revert_payload or {}).get("set_public", False))
