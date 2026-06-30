"""实体单位覆盖执行器：CRUD + 软删。

继承 CrudExecutorBase 复用 create/update/delete 默认实现（delete 软删 is_active=False、
revert restore_active 复活）。覆写 validate：
- create：按业务 entity_type+entity_id+unit_name 查重（带 is_active=True 过滤）
- update/delete：校验目标存在且 is_active=True（基类默认按 id 查不带过滤，子类补）

两种 entity_type 区分（关键，勿混）：
- 框架级 entity_type = "entity_unit_override"（本执行器注册名，进 change_proposals.entity_type）
- 业务级 entity_type（"ingredient"/"product"，来自 URL 路径，放 payload，create 时写入数据行）
"""
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.proposals.executors._crud_base import CrudExecutorBase
from app.models.entity_unit_override import EntityUnitOverride


class EntityUnitOverrideExecutor(CrudExecutorBase):
    entity_type = "entity_unit_override"
    model_class = EntityUnitOverride

    def validate(self, db: Session, proposal) -> None:
        action = proposal.action
        if action == "create":
            p = proposal.payload or {}
            biz_type = p.get("entity_type")
            biz_id = p.get("entity_id")
            unit_name = p.get("unit_name")
            if biz_type is None or biz_id is None or unit_name is None:
                raise HTTPException(
                    status_code=400,
                    detail="payload 缺少 entity_type/entity_id/unit_name",
                )
            dup = (
                db.query(EntityUnitOverride)
                .filter(
                    EntityUnitOverride.entity_type == biz_type,
                    EntityUnitOverride.entity_id == biz_id,
                    EntityUnitOverride.unit_name == unit_name,
                    EntityUnitOverride.is_active.is_(True),
                )
                .first()
            )
            if dup is not None:
                raise HTTPException(
                    status_code=400,
                    detail=f"{biz_type}/{biz_id} 已存在单位覆盖 '{unit_name}'",
                )
            return
        # update/delete：基类 validate 仅按 id 查存在性，这里补 is_active=True 校验
        eid = proposal.entity_id
        if eid is None:
            raise HTTPException(status_code=400, detail="update/delete 需 entity_id")
        obj = (
            db.query(EntityUnitOverride)
            .filter(
                EntityUnitOverride.id == eid,
                EntityUnitOverride.is_active.is_(True),
            )
            .first()
        )
        if obj is None:
            raise HTTPException(status_code=404, detail=f"实体单位覆盖 {eid} 不存在或已删除")

    def entity_label(self, db: Session, proposal) -> Optional[str]:
        """业务实体名（payload.entity_type/entity_id）+ unit_name。

        update/delete 时 entity_id 是 override.id，可补查其 unit_name。
        """
        from app.models.nutrition import Ingredient
        from app.models.product_entity import Product
        p = proposal.payload or {}
        biz_type = p.get("entity_type")
        biz_id = p.get("entity_id")
        unit_name = p.get("unit_name")
        parts = []
        if biz_type and biz_id is not None:
            if biz_type == "ingredient":
                ing = db.query(Ingredient).get(biz_id)
                if ing:
                    parts.append(f"原料「{ing.name}」")
            elif biz_type == "product":
                prod = db.query(Product).get(biz_id)
                if prod:
                    parts.append(f"商品「{prod.name}」")
        # update/delete 时 entity_id 是 override.id，可补查 unit_name
        if not unit_name and proposal.entity_id is not None:
            ov = db.query(EntityUnitOverride).get(proposal.entity_id)
            if ov:
                unit_name = ov.unit_name
        if unit_name:
            parts.append(f"单位「{unit_name}」")
        return " ".join(parts) if parts else None
