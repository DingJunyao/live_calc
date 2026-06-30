"""实体密度执行器：CRUD + 软删。与覆盖执行器同构。

密度无独立 update 端点，upsert 在 API 层判断 create/update（执行器只认标准三 action）。
condition 可为 None（默认密度），查询用 .is(None) 匹配。
"""
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.proposals.executors._crud_base import CrudExecutorBase
from app.models.entity_density import EntityDensity


class EntityDensityExecutor(CrudExecutorBase):
    entity_type = "entity_density"
    model_class = EntityDensity

    def validate(self, db: Session, proposal) -> None:
        action = proposal.action
        if action == "create":
            p = proposal.payload or {}
            biz_type = p.get("entity_type")
            biz_id = p.get("entity_id")
            condition = p.get("condition")
            if biz_type is None or biz_id is None:
                raise HTTPException(
                    status_code=400, detail="payload 缺少 entity_type/entity_id")
            if "density" not in p:
                raise HTTPException(status_code=400, detail="payload 缺少 density")
            dup = (
                db.query(EntityDensity)
                .filter(
                    EntityDensity.entity_type == biz_type,
                    EntityDensity.entity_id == biz_id,
                    EntityDensity.condition.is_(condition) if condition is None
                    else EntityDensity.condition == condition,
                    EntityDensity.is_active.is_(True),
                )
                .first()
            )
            if dup is not None:
                raise HTTPException(
                    status_code=400,
                    detail=f"{biz_type}/{biz_id} 已存在该 condition 的密度记录",
                )
            return
        eid = proposal.entity_id
        if eid is None:
            raise HTTPException(status_code=400, detail="update/delete 需 entity_id")
        obj = (
            db.query(EntityDensity)
            .filter(
                EntityDensity.id == eid,
                EntityDensity.is_active.is_(True),
            )
            .first()
        )
        if obj is None:
            raise HTTPException(status_code=404, detail=f"实体密度 {eid} 不存在或已删除")

    def entity_label(self, db: Session, proposal) -> Optional[str]:
        """业务实体名（payload.entity_type/entity_id）+ condition。"""
        from app.models.nutrition import Ingredient
        from app.models.product_entity import Product
        p = proposal.payload or {}
        biz_type = p.get("entity_type")
        biz_id = p.get("entity_id")
        condition = p.get("condition")
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
        if condition is None and proposal.entity_id is not None:
            d = db.query(EntityDensity).get(proposal.entity_id)
            if d:
                condition = d.condition
        if condition:
            parts.append(f"状态「{condition}」")
        return " ".join(parts) if parts else None
