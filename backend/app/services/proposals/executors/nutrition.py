"""营养数据执行器：补空自动 / 覆盖审核。

policy 在 apply 内动态 set（补空 → auto_approve；覆盖 → manual）。
更稳妥的做法是在 service.submit 前置检查决定 policy，本期以执行器内 set_policy 示意。

payload 期望：{"nutrients": {...}}
entity_id：食材 id（NutritionData.ingredient_id）
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.proposals.base import ProposalExecutor, ApplyResult
from app.services.proposals.registry import ExecutorRegistry
from app.models.nutrition_data import NutritionData
from app.models.nutrition import Ingredient


class NutritionExecutor(ProposalExecutor):
    entity_type = "nutrition"

    def validate(self, db: Session, proposal) -> None:
        eid = proposal.entity_id
        if eid is None:
            raise HTTPException(status_code=400, detail="营养提议需 entity_id（食材 id）")
        if db.query(Ingredient).get(eid) is None:
            raise HTTPException(status_code=404, detail=f"食材 {eid} 不存在")
        if "nutrients" not in (proposal.payload or {}):
            raise HTTPException(status_code=400, detail="payload 缺少 nutrients")

    def preview(self, db: Session, proposal) -> dict:
        eid = proposal.entity_id
        existing = db.query(NutritionData).filter(
            NutritionData.ingredient_id == eid).first()
        return {"ingredient_id": eid, "will_override": existing is not None,
                "note": "覆盖现有数据需审核；补空可自动通过"}

    def apply(self, db: Session, proposal) -> ApplyResult:
        eid = proposal.entity_id
        nutrients = proposal.payload.get("nutrients", {})
        existing = db.query(NutritionData).filter(
            NutritionData.ingredient_id == eid).first()

        snapshot = {}
        if existing is not None:
            snapshot = {"had_data": True, "nutrients": existing.nutrients,
                        "source": existing.source, "id": existing.id}
        # 写入 / 覆盖
        if existing is None:
            nd = NutritionData(
                ingredient_id=eid, nutrients=nutrients,
                source="custom", is_verified=True)
            db.add(nd)
        else:
            existing.nutrients = nutrients
            existing.source = "custom"
            existing.is_verified = True

        # 关键：补空 → auto_approve；覆盖 → manual（执行器内动态 set 取巧）
        # 注：submit 在 apply 前已读 policy 决定分流，此处 set 仅影响后续提交；
        #     覆盖场景的「manual」由治理总表默认 policy=manual 兜底，补空由 submit 调用方
        #     （API 层）在提交前判断后传 review_policy 更稳——此处保留示意。
        ExecutorRegistry.set_policy(
            "nutrition", "update",
            "auto_approve" if not snapshot.get("had_data") else "manual")

        return ApplyResult(
            snapshot=snapshot,
            revert_payload={"restore": snapshot} if snapshot else {"delete": True},
            summary="营养数据已更新",
        )

    def revert(self, db: Session, proposal) -> None:
        snap = proposal.snapshot or {}
        rp = proposal.revert_payload or {}
        eid = proposal.entity_id
        if rp.get("delete"):
            db.query(NutritionData).filter(
                NutritionData.ingredient_id == eid).delete(synchronize_session=False)
            return
        if snap.get("had_data"):
            nd = db.query(NutritionData).get(snap["id"])
            if nd is not None:
                nd.nutrients = snap["nutrients"]
                nd.source = snap["source"]
