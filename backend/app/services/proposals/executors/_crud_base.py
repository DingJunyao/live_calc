"""简单 CRUD 执行器基类：snapshot 原值 → apply 改 → revert 还原。

供 ingredient/unit/hierarchy/merchant 的 create/update/delete 复用（DRY）。
合并（merge）等复杂操作不走此基类，各自覆写 apply/revert。
"""
from decimal import Decimal
from datetime import date, datetime
from typing import Optional, Type
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.proposals.base import ProposalExecutor, ApplyResult


def _json_safe(v):
    """把 ORM 列值转成 JSON 可序列化类型（snapshot/revert_payload 存 JSON 列）。

    Decimal→str（无损，Numeric 列 setter 接受 str 自动转回 Decimal）；
    date/datetime→isoformat 字符串。
    """
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


class CrudExecutorBase(ProposalExecutor):
    """通用 CRUD 执行器基类。

    子类需声明：
      entity_type: str
      model_class: SQLAlchemy 模型类（必须能通过 db.query(model_class).get(eid) 取出）
    子类可在 apply 内先行 merge 特判后调 super().apply，或直接覆写。
    """

    model_class: Type = None  # 子类覆写

    def validate(self, db: Session, proposal) -> None:
        """默认校验：create 不要求 entity_id；update/delete 要求实体存在。"""
        action = proposal.action
        if action == "create":
            return
        eid = proposal.entity_id
        if eid is None:
            raise HTTPException(status_code=400, detail=f"{self.entity_type} update/delete 需 entity_id")
        if db.query(self.model_class).get(eid) is None:
            raise HTTPException(status_code=404, detail=f"{self.entity_type} {eid} 不存在")

    def preview(self, db: Session, proposal) -> dict:
        eid = proposal.entity_id
        obj = db.query(self.model_class).get(eid) if eid else None
        return {"entity_id": eid, "exists": obj is not None, "action": proposal.action}

    def entity_label(self, db: Session, proposal) -> Optional[str]:
        """默认：按 entity_id 查 model 的常见名称字段（name/title/username）。子类可覆写。"""
        eid = proposal.entity_id
        if eid is None:
            return None
        obj = db.query(self.model_class).get(eid)
        if obj is None:
            return None
        for attr in ("name", "title", "username"):
            v = getattr(obj, attr, None)
            if v:
                return str(v)
        return None

    def build_snapshot(self, db: Session, proposal) -> dict:
        """提交时预填的 before 快照（供审核员在 pending 时看原内容）。

        apply 时 _do_apply 会用 executor.apply 返回的 snapshot 覆盖（保证 apply 前最新值）。
        - update：payload 涉及字段的当前值
        - delete：全列当前值
        - create/其他：{}（无 before）
        """
        action = proposal.action
        if action not in ("update", "delete"):
            return {}
        eid = proposal.entity_id
        if eid is None:
            return {}
        obj = db.query(self.model_class).get(eid)
        if obj is None:
            return {}
        if action == "update":
            return {k: _json_safe(getattr(obj, k))
                    for k in (proposal.payload or {}) if hasattr(obj, k)}
        return {c.name: _json_safe(getattr(obj, c.name))
                for c in obj.__table__.columns}

    def apply(self, db: Session, proposal) -> ApplyResult:
        action = proposal.action
        eid = proposal.entity_id
        if action == "create":
            obj = self.model_class(**proposal.payload)
            db.add(obj)
            db.flush()
            return ApplyResult(
                snapshot={},
                revert_payload={"delete_id": obj.id},
                summary=f"已创建 {self.entity_type}",
            )
        obj = db.query(self.model_class).get(eid)
        if obj is None:
            raise HTTPException(status_code=404, detail=f"{self.entity_type} {eid} 不存在")
        if action == "update":
            # 仅快照 payload 中提及的字段
            snapshot = {k: _json_safe(getattr(obj, k)) for k in proposal.payload}
            for k, v in proposal.payload.items():
                setattr(obj, k, v)
            return ApplyResult(
                snapshot=snapshot,
                revert_payload={"restore": snapshot},
                summary=f"已更新 {self.entity_type} {eid}",
            )
        if action == "delete":
            snapshot = {c.name: _json_safe(getattr(obj, c.name)) for c in obj.__table__.columns}
            self._soft_delete(obj)
            return ApplyResult(
                snapshot=snapshot,
                revert_payload={"restore_active": True},
                summary=f"已软删 {self.entity_type} {eid}",
            )
        raise HTTPException(status_code=400, detail=f"未知 action: {action}")

    def revert(self, db: Session, proposal) -> None:
        rp = proposal.revert_payload or {}
        snap = proposal.snapshot or {}
        # create 回滚：删除新建行
        if "delete_id" in rp:
            obj = db.query(self.model_class).get(rp["delete_id"])
            if obj is not None:
                db.delete(obj)
            return
        eid = proposal.entity_id
        obj = db.query(self.model_class).get(eid) if eid else None
        # update 回滚：按快照还原字段
        if rp.get("restore"):
            if obj is not None:
                for k, v in rp["restore"].items():
                    setattr(obj, k, v)
            return
        # delete 回滚：复活（恢复 is_active）
        if rp.get("restore_active"):
            if obj is not None:
                self._restore(obj, snap)
            return

    def _soft_delete(self, obj) -> None:
        """软删：默认置 is_active=False（AuditMixin 提供）。子类可覆写（如 Merchant 用 is_open）。"""
        if hasattr(obj, "is_active"):
            obj.is_active = False
        else:
            raise NotImplementedError(f"{self.model_class.__name__} 无 is_active，子类需覆写 _soft_delete/_restore")

    def _restore(self, obj, snap) -> None:
        """复活：默认置 is_active=True。子类可覆写。"""
        if hasattr(obj, "is_active"):
            obj.is_active = True
