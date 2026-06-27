"""单位执行器：CRUD。validate 拒绝改 is_standard=True 的标准单位
（标准单位仅管理员直写或系统内置，不进提议框架）。"""
from fastapi import HTTPException

from app.services.proposals.executors._crud_base import CrudExecutorBase
from app.models.unit import Unit


class UnitExecutor(CrudExecutorBase):
    entity_type = "unit"
    model_class = Unit

    def validate(self, db, proposal) -> None:
        # update / delete 拒绝标准单位
        eid = proposal.entity_id
        if eid is not None and proposal.action in ("update", "delete"):
            u = db.query(Unit).get(eid)
            if u is not None and getattr(u, "is_standard", False):
                raise HTTPException(
                    status_code=403,
                    detail="标准单位仅管理员可改/删，不进提议框架")
        # create 拒绝 is_standard=True（标准单位不通过提议创建）
        if proposal.action == "create":
            if proposal.payload.get("is_standard"):
                raise HTTPException(
                    status_code=403,
                    detail="标准单位不可通过提议创建")
        super().validate(db, proposal)
