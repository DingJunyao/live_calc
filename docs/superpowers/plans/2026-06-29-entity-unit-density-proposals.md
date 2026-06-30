# 实体单位覆盖与实体密度 接入提议-审核框架 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 放开原料/商品的「实体单位覆盖」与「实体密度」5 个写端点给普通用户，接入 change_proposals 提议-审核框架（全 manual 审核 + 管理员直写即时生效 + 软删回滚）。

**Architecture:** 两表加 `is_active` 软删字段 + 拆唯一约束；新建 2 个执行器（继承 `CrudExecutorBase` 复用软删/复活）；`units.py` 5 个写端点做分流（管理员 `apply_as_admin` / 普通用户 `submit`）；12+ 下游读取点加 `is_active` 过滤；两个详情页前端按角色提示待审。

**Tech Stack:** FastAPI + SQLAlchemy 2.x + Alembic（SQLite dev / MySQL / PostgreSQL）；Vue 3 + Vuetify。

**项目约束（务必遵守）：**
- **不主动 `git commit` / 开分支**（项目 CLAUDE.md 明文规定）。每个任务以「测试通过 + `py_compile` / `npm run build` 无误」为完成标志，提交时机由用户决定。
- **不自行修改开发数据库**——本计划涉及表结构变更，对开发库 `backend/data/livecalc.db` 的补列操作属「表结构变更必需」，按项目先例（备份后手动执行 SQL，见 Task 1 Step 6），需在执行时显式向用户说明并备份。
- 后端改动用 `uv` 管理的虚拟环境（`.venv`）；前端改动须 `npm run build` 通过。
- 设计依据：[../specs/2026-06-29-entity-unit-density-proposals-design.md](../specs/2026-06-29-entity-unit-density-proposals-design.md)

---

## File Structure

### 后端新增
- `backend/app/services/proposals/executors/entity_unit_override.py` — `EntityUnitOverrideExecutor`，继承 CrudExecutorBase，覆写 validate（同名查重带 is_active + update/delete 校验活跃）
- `backend/app/services/proposals/executors/entity_density.py` — `EntityDensityExecutor`，同构
- `backend/alembic/versions/20260629_*_entity_unit_density_soft_delete.py` — ADD is_active + drop unique + 建复合索引
- `backend/scripts/sql/20260629_entity_unit_density_soft_delete_sqlite.sql`
- `backend/scripts/sql/20260629_entity_unit_density_soft_delete_mysql.sql`
- `backend/scripts/sql/20260629_entity_unit_density_soft_delete_postgres.sql`
- `backend/tests/test_entity_unit_density_proposals.py` — 端点分流集成测试

### 后端修改
- `backend/app/models/entity_unit_override.py` — +is_active，去 UniqueConstraint 改 Index
- `backend/app/models/entity_density.py` — 同
- `backend/app/api/units.py` — 5 个写端点分流
- `backend/app/services/proposals/bootstrap.py` — 注册 2 执行器（全 manual）
- `backend/app/services/unit_conversion_service.py` — 6+3 处加 is_active 过滤
- `backend/app/services/recipe_service.py` — 1 处加过滤
- `backend/app/services/importer/ai_inference/inferrer.py` — 3 处加过滤
- `backend/app/services/export/reachability.py` / `packaging.py` — 只收集活数据
- `backend/app/services/importer/importers/export.py` — upsert 查重加过滤

### 前端修改
- `frontend/src/views/ingredients/IngredientDetail.vue` — 4 写函数按角色提示
- `frontend/src/views/products/ProductDetail.vue` — 同
- `frontend/src/views/admin/ProposalsView.vue` — entityTypeLabel 补 2 项

---

## Task 1: 数据模型加 is_active + 拆唯一约束 + 迁移 + SQL 脚本

**Files:**
- Modify: `backend/app/models/entity_unit_override.py`
- Modify: `backend/app/models/entity_density.py`
- Create: `backend/alembic/versions/20260629_<rev>_entity_unit_density_soft_delete.py`
- Create: `backend/scripts/sql/20260629_entity_unit_density_soft_delete_sqlite.sql`
- Create: `backend/scripts/sql/20260629_entity_unit_density_soft_delete_mysql.sql`
- Create: `backend/scripts/sql/20260629_entity_unit_density_soft_delete_postgres.sql`

- [ ] **Step 1: 改 EntityUnitOverride 模型**

替换 [entity_unit_override.py](../../../backend/app/models/entity_unit_override.py) 全文：

```python
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class EntityUnitOverride(Base):
    """实体单位覆盖表，用于记录特定原料或商品的自定义单位换算。

    is_active 软删：delete 提议软删（is_active=False），revert 复活。
    原唯一约束 uq_entity_unit 已拆为普通复合索引，软删后同名重建不撞约束
    （应用层校验带 is_active=True 过滤，参照 ingredients 同名重建先例）。
    """
    __tablename__ = "entity_unit_overrides"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(20), nullable=False)  # 'ingredient' 或 'product'
    entity_id = Column(Integer, nullable=False)
    unit_name = Column(String(50), nullable=False)  # 如 "盒(12个)"、"根"
    base_unit_id = Column(Integer, ForeignKey("units.id"))  # 指向基础单位（如 "个"）
    conversion_factor = Column(Numeric(15, 10))  # 换算系数，如 12（一盒12个）
    weight_per_unit = Column(Numeric(10, 3))  # 单位重量，如 55（一个55g）
    weight_unit_id = Column(Integer, ForeignKey("units.id"))  # 指向质量单位
    is_default = Column(Boolean, default=False)  # 是否为该实体的默认单位
    source = Column(String(20), default="manual")  # import / manual / agent
    is_active = Column(Boolean, default=True, nullable=False, index=True)  # 软删标记
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        # 去唯一约束，改普通复合索引（软删后同名重建不撞约束，校验走应用层）
        Index("ix_entity_unit_active", "entity_type", "entity_id", "unit_name"),
    )

    # 关系
    base_unit = relationship("Unit", foreign_keys=[base_unit_id])
    weight_unit = relationship("Unit", foreign_keys=[weight_unit_id])
```

- [ ] **Step 2: 改 EntityDensity 模型**

替换 [entity_density.py](../../../backend/app/models/entity_density.py) 全文：

```python
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Index
from sqlalchemy.sql import func
from app.core.database import Base


class EntityDensity(Base):
    """实体密度表，用于记录特定原料或商品的密度数据（kg/m³）。

    is_active 软删：delete 提议软删，revert 复活。
    原唯一约束 uq_entity_density 已拆为普通复合索引。
    """
    __tablename__ = "entity_densities"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(20), nullable=False)  # 'ingredient' 或 'product'
    entity_id = Column(Integer, nullable=False)
    density = Column(Numeric(10, 6), nullable=False)  # 密度（kg/m³，SI 基准）
    temperature = Column(Numeric(5, 2))  # 参考温度（℃）
    condition = Column(String(100))  # 状态描述，如"切碎"、"压碎"等
    source = Column(String(200))  # 数据来源
    confidence = Column(Numeric(3, 2), default=1.0)  # 数据可信度
    is_active = Column(Boolean, default=True, nullable=False, index=True)  # 软删标记
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_entity_density_active", "entity_type", "entity_id", "condition"),
    )
```

- [ ] **Step 3: py_compile 验证模型无语法错误**

Run: `cd /d/code/live_calc/backend && python -m py_compile app/models/entity_unit_override.py app/models/entity_density.py`
Expected: 无输出（成功）。

- [ ] **Step 4: 写 alembic 迁移**

先取当前 head：
Run: `cd /d/code/live_calc/backend && python -m alembic heads`
Expected: 输出当前 head 的 `<revision>`（记下，填入下方 `down_revision` 与 `revision`）。

新建 `backend/alembic/versions/20260629_<rev>_entity_unit_density_soft_delete.py`（`<rev>` 用 alembic 生成的短 hash，或手写 `c0e1d2f3a4b5` 风格唯一串）：

```python
"""entity_unit_override and entity_density soft delete

Revision ID: c0e1d2f3a4b5
Revises: <填入 Step 4 取到的当前 head>
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c0e1d2f3a4b5"
down_revision = "<填入 Step 4 取到的当前 head>"
branch_labels = None
depends_on = None


def upgrade():
    # entity_unit_overrides：加 is_active + 去唯一约束 + 建复合索引
    with op.batch_alter_table("entity_unit_overrides", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1"))
        )
        batch_op.drop_constraint("uq_entity_unit", type_="unique")
    op.create_index(
        "ix_entity_unit_active", "entity_unit_overrides",
        ["entity_type", "entity_id", "unit_name"], unique=False,
    )
    op.create_index(
        "ix_entity_unit_overrides_is_active", "entity_unit_overrides",
        ["is_active"], unique=False,
    )

    # entity_densities：同
    with op.batch_alter_table("entity_densities", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1"))
        )
        batch_op.drop_constraint("uq_entity_density", type_="unique")
    op.create_index(
        "ix_entity_density_active", "entity_densities",
        ["entity_type", "entity_id", "condition"], unique=False,
    )
    op.create_index(
        "ix_entity_densities_is_active", "entity_densities",
        ["is_active"], unique=False,
    )


def downgrade():
    op.drop_index("ix_entity_densities_is_active", table_name="entity_densities")
    op.drop_index("ix_entity_density_active", table_name="entity_densities")
    with op.batch_alter_table("entity_densities", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_entity_density", ["entity_type", "entity_id", "condition"])
        batch_op.drop_column("is_active")

    op.drop_index("ix_entity_unit_overrides_is_active", table_name="entity_unit_overrides")
    op.drop_index("ix_entity_unit_active", table_name="entity_unit_overrides")
    with op.batch_alter_table("entity_unit_overrides", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_entity_unit", ["entity_type", "entity_id", "unit_name"])
        batch_op.drop_column("is_active")
```

> 说明：SQLite 上唯一约束是表级定义，`batch_alter_table` 会重建表去掉它；MySQL/PG 上 `drop_constraint` 直接生效。约束名 `uq_entity_unit` / `uq_entity_density` 取自原模型定义。若执行时报「约束不存在」（如 SQLite 某些版本唯一约束以匿名索引形式存在），改用 `batch_op.drop_index("uq_entity_unit")` 兜底。

- [ ] **Step 5: 写三引擎 SQL 脚本**

新建 `backend/scripts/sql/20260629_entity_unit_density_soft_delete_sqlite.sql`：

```sql
-- 实体单位覆盖 + 实体密度 软删改造（SQLite）
-- 现有数据 is_active 默认 1（True）。唯一约束以索引形式存在，DROP INDEX 移除。

-- entity_unit_overrides
ALTER TABLE entity_unit_overrides ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1;
DROP INDEX IF EXISTS uq_entity_unit;
CREATE INDEX IF NOT EXISTS ix_entity_unit_active
    ON entity_unit_overrides(entity_type, entity_id, unit_name);
CREATE INDEX IF NOT EXISTS ix_entity_unit_overrides_is_active
    ON entity_unit_overrides(is_active);

-- entity_densities
ALTER TABLE entity_densities ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1;
DROP INDEX IF EXISTS uq_entity_density;
CREATE INDEX IF NOT EXISTS ix_entity_density_active
    ON entity_densities(entity_type, entity_id, condition);
CREATE INDEX IF NOT EXISTS ix_entity_densities_is_active
    ON entity_densities(is_active);
```

新建 `backend/scripts/sql/20260629_entity_unit_density_soft_delete_mysql.sql`：

```sql
-- 实体单位覆盖 + 实体密度 软删改造（MySQL）

ALTER TABLE entity_unit_overrides
    ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE,
    DROP INDEX uq_entity_unit;
CREATE INDEX ix_entity_unit_active
    ON entity_unit_overrides(entity_type, entity_id, unit_name);
CREATE INDEX ix_entity_unit_overrides_is_active
    ON entity_unit_overrides(is_active);

ALTER TABLE entity_densities
    ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE,
    DROP INDEX uq_entity_density;
CREATE INDEX ix_entity_density_active
    ON entity_densities(entity_type, entity_id, condition);
CREATE INDEX ix_entity_densities_is_active
    ON entity_densities(is_active);
```

新建 `backend/scripts/sql/20260629_entity_unit_density_soft_delete_postgres.sql`：

```sql
-- 实体单位覆盖 + 实体密度 软删改造（PostgreSQL，未启用 PostGIS，纯字段/索引变更）

ALTER TABLE entity_unit_overrides
    ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE entity_unit_overrides DROP CONSTRAINT IF EXISTS uq_entity_unit;
CREATE INDEX IF NOT EXISTS ix_entity_unit_active
    ON entity_unit_overrides(entity_type, entity_id, unit_name);
CREATE INDEX IF NOT EXISTS ix_entity_unit_overrides_is_active
    ON entity_unit_overrides(is_active);

ALTER TABLE entity_densities
    ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE entity_densities DROP CONSTRAINT IF EXISTS uq_entity_density;
CREATE INDEX IF NOT EXISTS ix_entity_density_active
    ON entity_densities(entity_type, entity_id, condition);
CREATE INDEX IF NOT EXISTS ix_entity_densities_is_active
    ON entity_densities(is_active);
```

- [ ] **Step 6: 补开发库（表结构变更必需，备份后执行）**

开发库 `backend/data/livecalc.db` 由 `create_all` 建库、未走 alembic（见 [cc/BUGFIX_共享转型表结构漂移.md](../../../cc/BUGFIX_共享转型表结构漂移.md) 先例），需手动补列。

**执行前先备份**：
Run: `cp backend/data/livecalc.db "backend/data/livecalc.db.bak_$(date +%Y%m%d_%H%M%S)""`

**执行 SQLite 脚本**（用项目 venv 的 sqlite 或 sqlite3 CLI）：
Run: `cd /d/code/live_calc/backend && python -c "import sqlite3; sqlite3.connect('data/livecalc.db').executescript(open('scripts/sql/20260629_entity_unit_density_soft_delete_sqlite.sql').read())"`

**验证列已加**：
Run: `python -c "import sqlite3; c=sqlite3.connect('backend/data/livecalc.db'); print([r[1] for r in c.execute('PRAGMA table_info(entity_unit_overrides)')]); print([r[1] for r in c.execute('PRAGMA table_info(entity_densities)')])"`
Expected: 两个列表都含 `is_active`。

- [ ] **Step 7: 写模型层测试（内存库自动建最新 schema）**

Create `backend/tests/models/test_entity_soft_delete.py`：

```python
"""实体单位覆盖/密度 软删字段模型层测试。

内存库 Base.metadata.create_all 自动按最新模型建表（含 is_active），
无需跑 alembic 迁移。验证字段存在 + 默认 True + 同名软删后可重建。
"""
from app.models.entity_unit_override import EntityUnitOverride
from app.models.entity_density import EntityDensity


def test_override_has_is_active_default_true(db_session):
    o = EntityUnitOverride(
        entity_type="ingredient", entity_id=1, unit_name="盒",
        weight_per_unit=55, is_active=True,
    )
    db_session.add(o)
    db_session.commit()
    db_session.refresh(o)
    assert o.is_active is True or o.is_active == 1  # SQLite Boolean 存为 int


def test_override_same_name_rebuild_after_soft_delete(db_session):
    """软删后同名重建不撞约束（唯一约束已拆）。"""
    o1 = EntityUnitOverride(entity_type="ingredient", entity_id=1, unit_name="盒", is_active=True)
    db_session.add(o1)
    db_session.commit()
    o1.is_active = False
    db_session.commit()
    # 软删后可重建同名
    o2 = EntityUnitOverride(entity_type="ingredient", entity_id=1, unit_name="盒", is_active=True)
    db_session.add(o2)
    db_session.commit()  # 不应抛 IntegrityError
    assert db_session.query(EntityUnitOverride).filter_by(
        entity_type="ingredient", entity_id=1, unit_name="盒", is_active=True).count() == 1


def test_density_has_is_active_default_true(db_session):
    d = EntityDensity(entity_type="ingredient", entity_id=1, density=780, is_active=True)
    db_session.add(d)
    db_session.commit()
    db_session.refresh(d)
    assert d.is_active is True or d.is_active == 1
```

- [ ] **Step 8: 运行模型测试**

Run: `cd /d/code/live_calc/backend && python -m pytest tests/models/test_entity_soft_delete.py -v`
Expected: 3 passed。

---

## Task 2: 两个新执行器 + 单元测试

**Files:**
- Create: `backend/app/services/proposals/executors/entity_unit_override.py`
- Create: `backend/app/services/proposals/executors/entity_density.py`
- Test: `backend/tests/test_entity_executors.py`

- [ ] **Step 1: 写 EntityUnitOverrideExecutor**

Create `backend/app/services/proposals/executors/entity_unit_override.py`：

```python
"""实体单位覆盖执行器：CRUD + 软删。

继承 CrudExecutorBase 复用 create/update/delete 默认实现（delete 软删 is_active=False、
revert restore_active 复活）。覆写 validate：
- create：按业务 entity_type+entity_id+unit_name 查重（带 is_active=True 过滤）
- update/delete：校验目标存在且 is_active=True（基类默认按 id 查不带过滤，子类补）

两种 entity_type 区分（关键，勿混）：
- 框架级 entity_type = "entity_unit_override"（本执行器注册名，进 change_proposals.entity_type）
- 业务级 entity_type（"ingredient"/"product"，来自 URL 路径，放 payload，create 时写入数据行）
"""
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
```

- [ ] **Step 2: 写 EntityDensityExecutor**

Create `backend/app/services/proposals/executors/entity_density.py`：

```python
"""实体密度执行器：CRUD + 软删。与覆盖执行器同构。

密度无独立 update 端点，upsert 在 API 层判断 create/update（执行器只认标准三 action）。
condition 可为 None（默认密度），查询用 .is(None) 匹配。
"""
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
```

- [ ] **Step 3: py_compile**

Run: `cd /d/code/live_calc/backend && python -m py_compile app/services/proposals/executors/entity_unit_override.py app/services/proposals/executors/entity_density.py`
Expected: 无输出。

- [ ] **Step 4: 写执行器单元测试**

Create `backend/tests/test_entity_executors.py`：

```python
"""实体单位覆盖/密度执行器 apply/revert 单元测试。

直接用 db_session 内存库测执行器，不经 API 层。
"""
import pytest
from types import SimpleNamespace

from app.services.proposals.executors.entity_unit_override import EntityUnitOverrideExecutor
from app.services.proposals.executors.entity_density import EntityDensityExecutor
from app.models.entity_unit_override import EntityUnitOverride
from app.models.entity_density import EntityDensity


def _proposal(action, payload, entity_id=None):
    return SimpleNamespace(
        action=action, payload=payload, entity_id=entity_id,
        snapshot=None, revert_payload=None,
    )


def test_override_create_apply_revert(db_session):
    ex = EntityUnitOverrideExecutor()
    p = _proposal("create", {
        "entity_type": "ingredient", "entity_id": 1, "unit_name": "盒",
        "weight_per_unit": 55, "is_active": True,
    })
    result = ex.apply(db_session, p)
    db_session.commit()
    created = db_session.query(EntityUnitOverride).filter_by(
        entity_type="ingredient", entity_id=1, unit_name="盒").first()
    assert created is not None and created.is_active in (True, 1)
    assert result.revert_payload["delete_id"] == created.id
    # revert（按 apply 返回的 revert_payload）
    p.revert_payload = result.revert_payload
    ex.revert(db_session, p)
    db_session.commit()
    assert db_session.query(EntityUnitOverride).filter_by(id=created.id).first() is None


def test_override_delete_soft_then_revert(db_session):
    ex = EntityUnitOverrideExecutor()
    o = EntityUnitOverride(entity_type="ingredient", entity_id=1, unit_name="盒", is_active=True)
    db_session.add(o)
    db_session.commit()
    db_session.refresh(o)
    p = _proposal("delete", {}, entity_id=o.id)
    result = ex.apply(db_session, p)
    db_session.commit()
    db_session.refresh(o)
    assert o.is_active in (False, 0)  # 软删
    # revert 复活
    p.revert_payload = result.revert_payload
    p.snapshot = result.snapshot
    ex.revert(db_session, p)
    db_session.commit()
    db_session.refresh(o)
    assert o.is_active in (True, 1)


def test_override_create_duplicate_rejected(db_session):
    ex = EntityUnitOverrideExecutor()
    db_session.add(EntityUnitOverride(
        entity_type="ingredient", entity_id=1, unit_name="盒", is_active=True))
    db_session.commit()
    p = _proposal("create", {
        "entity_type": "ingredient", "entity_id": 1, "unit_name": "盒", "is_active": True,
    })
    with pytest.raises(Exception):
        ex.validate(db_session, p)


def test_density_delete_soft_then_revert(db_session):
    ex = EntityDensityExecutor()
    d = EntityDensity(entity_type="ingredient", entity_id=1, density=780, is_active=True)
    db_session.add(d)
    db_session.commit()
    db_session.refresh(d)
    p = _proposal("delete", {}, entity_id=d.id)
    result = ex.apply(db_session, p)
    db_session.commit()
    db_session.refresh(d)
    assert d.is_active in (False, 0)
    p.revert_payload = result.revert_payload
    p.snapshot = result.snapshot
    ex.revert(db_session, p)
    db_session.commit()
    db_session.refresh(d)
    assert d.is_active in (True, 1)
```

- [ ] **Step 5: 运行执行器测试**

Run: `cd /d/code/live_calc/backend && python -m pytest tests/test_entity_executors.py -v`
Expected: 4 passed。

---

## Task 3: bootstrap 注册两个执行器

**Files:**
- Modify: `backend/app/services/proposals/bootstrap.py`

- [ ] **Step 1: 注册执行器**

在 [bootstrap.py](../../../backend/app/services/proposals/bootstrap.py) 顶部 import 区加：

```python
from app.services.proposals.executors.entity_unit_override import EntityUnitOverrideExecutor
from app.services.proposals.executors.entity_density import EntityDensityExecutor
```

在 `register_all` 函数内、`# 加载持久化策略覆盖默认` 注释**之前**加（全 manual，无需 set_policy 细分）：

```python
    # 实体单位覆盖：全 manual（新增/编辑/删除均需审核，用户加严要求）
    ExecutorRegistry.register(EntityUnitOverrideExecutor(), default_policy="manual", default_risk="mid")

    # 实体密度：全 manual
    ExecutorRegistry.register(EntityDensityExecutor(), default_policy="manual", default_risk="mid")
```

- [ ] **Step 2: py_compile**

Run: `cd /d/code/live_calc/backend && python -m py_compile app/services/proposals/bootstrap.py`
Expected: 无输出。

- [ ] **Step 3: 写注册验证测试**

追加到 `backend/tests/test_entity_executors.py` 末尾：

```python
def test_executors_registered_manual(db_session):
    from app.services.proposals.bootstrap import register_all
    from app.services.proposals.registry import ExecutorRegistry
    register_all()
    assert ExecutorRegistry.get("entity_unit_override") is not None
    assert ExecutorRegistry.get("entity_density") is not None
    assert ExecutorRegistry.policy_for("entity_unit_override", "create") == "manual"
    assert ExecutorRegistry.policy_for("entity_density", "delete") == "manual"
```

- [ ] **Step 4: 运行测试**

Run: `cd /d/code/live_calc/backend && python -m pytest tests/test_entity_executors.py::test_executors_registered_manual -v`
Expected: passed。

---

## Task 4: 下游读取点加 is_active 过滤

> 关键任务：12+ 处读取点漏一处即成本计算读到「幽灵数据」。每处加 `.filter(... is_active.is_(True))`。完成后 grep 全量比对。

**Files:**
- Modify: `backend/app/services/unit_conversion_service.py`（L122/142/161/311/330/348/512/554/663）
- Modify: `backend/app/services/recipe_service.py`（L1834）
- Modify: `backend/app/services/importer/ai_inference/inferrer.py`（L468/562/597）
- Modify: `backend/app/services/export/reachability.py`（L81/83/221/227/240/246）

- [ ] **Step 1: unit_conversion_service.py 加过滤**

该文件有 9 个查询点。通用改法：每个 `.filter(...)` 链里追加一条 `EntityUnitOverride.is_active.is_(True)` 或 `EntityDensity.is_active.is_(True)`。

逐处定位（用 `grep -n "EntityUnitOverride\|EntityDensity" backend/app/services/unit_conversion_service.py` 找到每处 `db.query(...).filter(...)`），在每处的 filter 里补 is_active。示例（密度查询，L122 附近）：

改前：
```python
self.db.query(EntityDensity)
.filter(
    EntityDensity.entity_type == entity_type,
    EntityDensity.entity_id == entity_id,
)
.order_by(EntityDensity.confidence.desc())
```
改后：
```python
self.db.query(EntityDensity)
.filter(
    EntityDensity.entity_type == entity_type,
    EntityDensity.entity_id == entity_id,
    EntityDensity.is_active.is_(True),
)
.order_by(EntityDensity.confidence.desc())
```

对 9 处（3 个 EntityDensity + 6 个 EntityUnitOverride）逐一加同样过滤。L663 的 `db.query(EntityUnitOverride.unit_name)` select 投影查询同样补 `EntityUnitOverride.is_active.is_(True)`。

- [ ] **Step 2: recipe_service.py:1834 加过滤**

定位 `db.query(EntityUnitOverride).filter(` （[recipe_service.py:1834](../../../backend/app/services/recipe_service.py#L1834)），在 filter 链补：

```python
EntityUnitOverride.is_active.is_(True),
```

- [ ] **Step 3: inferrer.py 加过滤（3 处）**

定位 L468/562/597 三处 `db.query(EntityDensity...)`，每处 filter 补 `EntityDensity.is_active.is_(True)`。L597 是 `db.query(EntityDensity.entity_id)` 投影查询同样补。

- [ ] **Step 4: export/reachability.py 只收集活数据**

L81/83 的全集查询（`db.query(EntityDensity).all()` / `db.query(EntityUnitOverride).all()`）改为带过滤：
```python
es.entity_density_ids = {d.id for d in db.query(EntityDensity).filter(EntityDensity.is_active.is_(True)).all()}
es.entity_unit_override_ids = {o.id for o in db.query(EntityUnitOverride).filter(EntityUnitOverride.is_active.is_(True)).all()}
```

L221/227/240/246 的按 entity_id 集合过滤查询，filter 链补 `EntityDensity.is_active.is_(True)` / `EntityUnitOverride.is_active.is_(True)`。

> packaging.py 用 `id.in_(es.entity_*_ids)` 查询——id 集合已由 reachability 过滤为活数据，packaging 无需改。importer/importers/export.py:240 的 upsert 查重 filter 补 `EntityDensity.is_active.is_(True)`。

- [ ] **Step 5: importer/importers/export.py:240 加过滤**

定位 L240 `db.query(EntityDensity).filter(` 查重，补 `EntityDensity.is_active.is_(True)`。

- [ ] **Step 6: py_compile 全部改动文件**

Run:
```
cd /d/code/live_calc/backend && python -m py_compile app/services/unit_conversion_service.py app/services/recipe_service.py app/services/importer/ai_inference/inferrer.py app/services/export/reachability.py app/services/importer/importers/export.py
```
Expected: 无输出。

- [ ] **Step 7: grep 全量比对，确保无遗漏**

Run: `cd /d/code/live_calc/backend && grep -rn "EntityUnitOverride\|EntityDensity" app/services/ --include="*.py" | grep "db.query\|\.filter\|\.all\|\.first" | grep -v "is_active"`
Expected: 输出的每一行都需人工确认——若是查询点且无 is_active 过滤则补；若是 import 语句或非查询则忽略。目标是**所有查询点都带 is_active 过滤**（写入点 add/new 不算）。

- [ ] **Step 8: 写过滤回归测试**

追加到 `backend/tests/test_entity_executors.py`：

```python
def test_downstream_filter_excludes_soft_deleted(db_session):
    """软删的覆盖/密度不应被换算服务读到（防幽灵数据）。"""
    from app.services.unit_conversion_service import UnitConversionService
    # 活跃(weight=10) + 软删(weight=99) 各一条同名覆盖
    live = EntityUnitOverride(entity_type="ingredient", entity_id=9991,
                              unit_name="X", weight_per_unit=10, is_active=True)
    dead = EntityUnitOverride(entity_type="ingredient", entity_id=9991,
                              unit_name="X", weight_per_unit=99, is_active=False)
    db_session.add_all([live, dead])
    db_session.commit()
    ucs = UnitConversionService(db_session)
    # get_entity_override 加了 is_active 过滤后只返回活跃那条
    found = ucs.get_entity_override("ingredient", 9991, "X")
    assert found is not None
    assert float(found.weight_per_unit) == 10.0  # 活跃值，非软删的 99


def test_downstream_density_filter_excludes_soft_deleted(db_session):
    """软删的密度（高 confidence）不应被 get_density 读到。"""
    from app.services.unit_conversion_service import UnitConversionService
    from app.models.entity_density import EntityDensity
    db_session.add(EntityDensity(entity_type="ingredient", entity_id=9992,
                                 density=1234, confidence=0.99, is_active=False))  # 软删高
    db_session.add(EntityDensity(entity_type="ingredient", entity_id=9992,
                                 density=780, confidence=0.5, is_active=True))   # 活跃低
    db_session.commit()
    ucs = UnitConversionService(db_session)
    # 加过滤后只读活跃的 780，而非软删高 confidence 的 1234
    assert float(ucs.get_density("ingredient", 9992)) == 780.0
```

- [ ] **Step 9: 运行过滤测试**

Run: `cd /d/code/live_calc/backend && python -m pytest tests/test_entity_executors.py::test_downstream_filter_excludes_soft_deleted -v`
Expected: passed。若 FAIL（读到 99），说明某处过滤遗漏，回 Step 1-5 补。

---

## Task 5: 端点分流（units.py 5 个写端点）+ 集成测试

**Files:**
- Modify: `backend/app/api/units.py`（create/update/delete_entity_unit_override + upsert/delete_entity_density）
- Test: `backend/tests/test_entity_unit_density_proposals.py`

- [ ] **Step 1: create_entity_unit_override 分流**

替换 [units.py:457-498](../../../backend/app/api/units.py#L457) 的 `create_entity_unit_override` 函数：

```python
@entities_unit_router.post("", response_model=EntityUnitOverrideResponse, status_code=201)
@entities_unit_router.post("/", response_model=EntityUnitOverrideResponse, status_code=201)
def create_entity_unit_override(
    entity_type: str,
    entity_id: int,
    data: EntityUnitOverrideCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建实体单位覆盖（分流：管理员直写 / 普通用户提议）。

    全 manual——普通用户提交后待管理员审核（同名查重在执行器 validate 带 is_active 过滤）。
    """
    _validate_entity_type(entity_type)
    payload = {"entity_type": entity_type, "entity_id": entity_id, **data.model_dump()}

    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="entity_unit_override", entity_id=None,
            action="create", payload=payload, admin=current_user,
        )
        db.commit()
        return (
            db.query(EntityUnitOverride)
            .filter(
                EntityUnitOverride.entity_type == entity_type,
                EntityUnitOverride.entity_id == entity_id,
                EntityUnitOverride.unit_name == data.unit_name,
                EntityUnitOverride.is_active.is_(True),
            )
            .order_by(EntityUnitOverride.id.desc())
            .first()
        )

    p = proposal_service.submit(
        db, entity_type="entity_unit_override", entity_id=None,
        action="create", payload=payload, proposer=current_user,
    )
    db.commit()
    # manual → status=pending；返回占位骨架满足 response_model
    return EntityUnitOverride(
        id=0, entity_type=entity_type, entity_id=entity_id,
        unit_name=data.unit_name,
    )
```

- [ ] **Step 2: update_entity_unit_override 分流**

替换 [units.py:501-537](../../../backend/app/api/units.py#L501) 的 `update_entity_unit_override`：

```python
@entities_unit_router.put("/{override_id}", response_model=EntityUnitOverrideResponse)
def update_entity_unit_override(
    entity_type: str,
    entity_id: int,
    override_id: int,
    data: EntityUnitOverrideUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新实体单位覆盖（分流）。普通用户待审：值未变，返回当前对象。"""
    _validate_entity_type(entity_type)
    # 路径校验：override 属于该实体且活跃（执行器 validate 也会校验活跃）
    obj = (
        db.query(EntityUnitOverride)
        .filter(
            EntityUnitOverride.id == override_id,
            EntityUnitOverride.entity_type == entity_type,
            EntityUnitOverride.entity_id == entity_id,
            EntityUnitOverride.is_active.is_(True),
        )
        .first()
    )
    if not obj:
        raise HTTPException(status_code=404, detail="实体单位覆盖不存在")

    update_data = data.model_dump(exclude_unset=True)

    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="entity_unit_override", entity_id=override_id,
            action="update", payload=update_data, admin=current_user,
        )
        db.commit()
        db.refresh(obj)
        return obj

    proposal_service.submit(
        db, entity_type="entity_unit_override", entity_id=override_id,
        action="update", payload=update_data, proposer=current_user,
    )
    db.commit()
    db.refresh(obj)
    return obj  # 待审：值未变
```

- [ ] **Step 3: delete_entity_unit_override 分流**

替换 [units.py:540-571](../../../backend/app/api/units.py#L540) 的 `delete_entity_unit_override`：

```python
@entities_unit_router.delete("/{override_id}")
def delete_entity_unit_override(
    entity_type: str,
    entity_id: int,
    override_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除实体单位覆盖（分流，软删）。普通用户待审。"""
    _validate_entity_type(entity_type)
    obj = (
        db.query(EntityUnitOverride)
        .filter(
            EntityUnitOverride.id == override_id,
            EntityUnitOverride.entity_type == entity_type,
            EntityUnitOverride.entity_id == entity_id,
            EntityUnitOverride.is_active.is_(True),
        )
        .first()
    )
    if not obj:
        raise HTTPException(status_code=404, detail="实体单位覆盖不存在")

    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="entity_unit_override", entity_id=override_id,
            action="delete", payload={}, admin=current_user,
        )
        db.commit()
        return {"message": "实体单位覆盖已删除（管理员直写，软删）"}

    p = proposal_service.submit(
        db, entity_type="entity_unit_override", entity_id=override_id,
        action="delete", payload={}, proposer=current_user,
    )
    db.commit()
    return {"message": f"删除提议已提交（proposal_id={p.id}, status={p.status}）"}
```

- [ ] **Step 4: upsert_entity_density 分流（端点层判断 create/update）**

替换 [units.py:628-678](../../../backend/app/api/units.py#L628) 的 `upsert_entity_density`：

```python
@entities_density_router.post("", response_model=EntityDensityResponse)
@entities_density_router.post("/", response_model=EntityDensityResponse)
def upsert_entity_density(
    entity_type: str,
    entity_id: int,
    data: EntityDensityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建或更新实体密度（upsert，分流）。

    全 manual。端点层先按 entity_type+entity_id+condition 查活跃记录——
    有则 submit/apply update，无则 submit/apply create。
    """
    _validate_entity_type(entity_type)
    existing = (
        db.query(EntityDensity)
        .filter(
            EntityDensity.entity_type == entity_type,
            EntityDensity.entity_id == entity_id,
            EntityDensity.condition.is_(data.condition) if data.condition is None
            else EntityDensity.condition == data.condition,
            EntityDensity.is_active.is_(True),
        )
        .first()
    )

    if existing:
        update_data = data.model_dump(exclude_unset=True)
        if current_user.is_admin:
            proposal_service.apply_as_admin(
                db, entity_type="entity_density", entity_id=existing.id,
                action="update", payload=update_data, admin=current_user,
            )
            db.commit()
            db.refresh(existing)
            return existing
        proposal_service.submit(
            db, entity_type="entity_density", entity_id=existing.id,
            action="update", payload=update_data, proposer=current_user,
        )
        db.commit()
        db.refresh(existing)
        return existing  # 待审：值未变

    # create 路径
    base = {"entity_type": entity_type, "entity_id": entity_id, **data.model_dump()}
    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="entity_density", entity_id=None,
            action="create", payload=base, admin=current_user,
        )
        db.commit()
        return (
            db.query(EntityDensity)
            .filter(
                EntityDensity.entity_type == entity_type,
                EntityDensity.entity_id == entity_id,
                EntityDensity.is_active.is_(True),
            )
            .order_by(EntityDensity.id.desc())
            .first()
        )
    p = proposal_service.submit(
        db, entity_type="entity_density", entity_id=None,
        action="create", payload=base, proposer=current_user,
    )
    db.commit()
    return EntityDensity(
        id=0, entity_type=entity_type, entity_id=entity_id, density=data.density,
    )
```

- [ ] **Step 5: delete_entity_density 分流**

替换 [units.py:681-712](../../../backend/app/api/units.py#L681) 的 `delete_entity_density`：

```python
@entities_density_router.delete("/{density_id}")
def delete_entity_density(
    entity_type: str,
    entity_id: int,
    density_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除实体密度（分流，软删）。普通用户待审。"""
    _validate_entity_type(entity_type)
    obj = (
        db.query(EntityDensity)
        .filter(
            EntityDensity.id == density_id,
            EntityDensity.entity_type == entity_type,
            EntityDensity.entity_id == entity_id,
            EntityDensity.is_active.is_(True),
        )
        .first()
    )
    if not obj:
        raise HTTPException(status_code=404, detail="实体密度记录不存在")

    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="entity_density", entity_id=density_id,
            action="delete", payload={}, admin=current_user,
        )
        db.commit()
        return {"message": "实体密度记录已删除（管理员直写，软删）"}

    p = proposal_service.submit(
        db, entity_type="entity_density", entity_id=density_id,
        action="delete", payload={}, proposer=current_user,
    )
    db.commit()
    return {"message": f"删除提议已提交（proposal_id={p.id}, status={p.status}）"}
```

- [ ] **Step 6: py_compile**

Run: `cd /d/code/live_calc/backend && python -m py_compile app/api/units.py`
Expected: 无输出。

- [ ] **Step 7: 写端点分流集成测试**

Create `backend/tests/test_entity_unit_density_proposals.py`：

```python
"""实体单位覆盖/密度 端点分流集成测试。

管理员直写即时生效；普通用户全 manual 待审（列表不出现待定值）。
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.proposals.bootstrap import register_all

client = TestClient(app)


@pytest.fixture(autouse=True)
def _setup():
    """TestClient 不触发 main.py lifespan，需显式注册执行器。"""
    register_all()
    previous = dict(app.dependency_overrides)
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)


def _ingredient(db_session):
    from app.models.nutrition import Ingredient
    ing = Ingredient(name="测试食材_xyz", is_active=True)
    db_session.add(ing)
    db_session.commit()
    db_session.refresh(ing)
    return ing.id


def test_admin_create_override_applied(db_session, as_admin):
    ing_id = _ingredient(db_session)
    resp = client.post(
        f"/api/v1/entities/ingredient/{ing_id}/units",
        json={"unit_name": "盒", "weight_per_unit": 55},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] != 0  # 管理员即时生效，返回真实 id
    assert body["unit_name"] == "盒"


def test_non_admin_create_override_pending(db_session, as_non_admin):
    ing_id = _ingredient(db_session)
    resp = client.post(
        f"/api/v1/entities/ingredient/{ing_id}/units",
        json={"unit_name": "盒", "weight_per_unit": 55},
    )
    assert resp.status_code == 201
    assert resp.json()["id"] == 0  # 占位骨架，待审
    # 列表不出现待定值
    lst = client.get(f"/api/v1/entities/ingredient/{ing_id}/units").json()
    assert all(u["unit_name"] != "盒" for u in lst)


def test_non_admin_delete_override_pending(db_session, as_non_admin):
    """已存在的覆盖，普通用户提交删除提议（待审，不立即删）。

    用 db_session 直接建数据（绕过 API，避免一个用例切两个身份）；
    db_session 与 as_non_admin 的 client 共享同一内存库（TestingSessionLocal + StaticPool）。
    """
    from app.models.entity_unit_override import EntityUnitOverride
    ing_id = _ingredient(db_session)
    o = EntityUnitOverride(entity_type="ingredient", entity_id=ing_id,
                           unit_name="袋", weight_per_unit=30, is_active=True)
    db_session.add(o)
    db_session.commit()
    db_session.refresh(o)
    oid = o.id
    resp = client.delete(f"/api/v1/entities/ingredient/{ing_id}/units/{oid}")
    assert resp.status_code == 200
    assert "已提交" in resp.json()["message"]
    # 列表仍有该单位（待审未删）
    lst = client.get(f"/api/v1/entities/ingredient/{ing_id}/units").json()
    assert any(u["id"] == oid for u in lst)


def test_non_admin_create_density_pending(db_session, as_non_admin):
    ing_id = _ingredient(db_session)
    resp = client.post(
        f"/api/v1/entities/ingredient/{ing_id}/density",
        json={"density": 780, "source": "估测"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == 0  # 占位，待审
    lst = client.get(f"/api/v1/entities/ingredient/{ing_id}/density").json()
    assert all(not (float(d["density"]) == 780.0) for d in lst)
```

- [ ] **Step 8: 运行集成测试**

Run: `cd /d/code/live_calc/backend && python -m pytest tests/test_entity_unit_density_proposals.py -v`
Expected: 4 passed。

> 若 Ingredient 模型字段或 `name` 列名不同，用 `grep -n "class Ingredient" backend/app/models/nutrition.py` 确认必填字段后调整 `_ingredient` 辅助函数。

---

## Task 6: 前端适配（两个详情页 + 审核台 i18n）

**Files:**
- Modify: `frontend/src/views/ingredients/IngredientDetail.vue`（saveEntityUnit L2431 / deleteEntityUnit L2461 / saveDensity L2495 / deleteDensity L2523）
- Modify: `frontend/src/views/products/ProductDetail.vue`（同 4 函数 L1605/1635/1669/1697）
- Modify: `frontend/src/views/admin/ProposalsView.vue`（entityTypeLabel）

- [ ] **Step 1: IngredientDetail.vue 4 写函数按角色提示**

前端判断管理员用 `userStore.user?.is_admin`（本文件 L450 已有此用法）。在 `<script setup>` 顶部确保已引入 userStore（若未引入，加 `import { useUserStore } from '@/stores/user'` 并 `const userStore = useUserStore()`；参照 [ProposalsView.vue:536](../../../frontend/src/views/admin/ProposalsView.vue#L536)）。

替换 `saveEntityUnit`（[L2431](../../../frontend/src/views/ingredients/IngredientDetail.vue#L2431)）的 try 块成功分支：

```javascript
    if (unitForm.value.id) {
      await api.put(`/entities/ingredient/${ingredientId.value}/units/${unitForm.value.id}`, payload)
    } else {
      await api.post(`/entities/ingredient/${ingredientId.value}/units`, payload)
    }
    if (userStore.user?.is_admin) {
      showMessage('保存成功', 'success')
      showUnitDialog.value = false
      await loadEntityUnits()
      await loadUnmappedUnits()
    } else {
      showMessage('已提交，待管理员审核', 'info')
      showUnitDialog.value = false
    }
```

替换 `deleteEntityUnit`（[L2461](../../../frontend/src/views/ingredients/IngredientDetail.vue#L2461)）try 块：

```javascript
    await api.delete(`/entities/ingredient/${ingredientId.value}/units/${unitId}`)
    if (userStore.user?.is_admin) {
      showMessage('删除成功', 'success')
      await loadEntityUnits()
      await loadUnmappedUnits()
    } else {
      showMessage('删除提议已提交，待管理员审核', 'info')
    }
```

替换 `saveDensity`（[L2495](../../../frontend/src/views/ingredients/IngredientDetail.vue#L2495)）try 块成功分支（保留 kg/m³ 换算逻辑）：

```javascript
    await api.post(`/entities/ingredient/${ingredientId.value}/density`, {
      density: density,
      temperature: densityForm.value.temperature,
      source: densityForm.value.source
    })
    if (userStore.user?.is_admin) {
      showMessage('保存成功', 'success')
      showDensityDialog.value = false
      await loadDensity()
    } else {
      showMessage('已提交，待管理员审核', 'info')
      showDensityDialog.value = false
    }
```

替换 `deleteDensity`（[L2523](../../../frontend/src/views/ingredients/IngredientDetail.vue#L2523)）try 块：

```javascript
    await api.delete(`/entities/ingredient/${ingredientId.value}/density/${densityId}`)
    if (userStore.user?.is_admin) {
      showMessage('删除成功', 'success')
      entityDensity.value = null
    } else {
      showMessage('删除提议已提交，待管理员审核', 'info')
    }
```

- [ ] **Step 2: ProductDetail.vue 4 写函数同样改造**

对 [ProductDetail.vue](../../../frontend/src/views/products/ProductDetail.vue) 的 `saveEntityUnit`（L1605）/ `deleteEntityUnit`（L1635）/ `saveDensity`（L1669）/ `deleteDensity`（L1697）做与 Step 1 完全相同的改造，仅把 URL 中的 `ingredient` 换成 `product`、`ingredientId.value` 换成 `productId.value`。同样确保 userStore 已引入。

- [ ] **Step 3: ProposalsView.vue 补 entityTypeLabel**

在 [ProposalsView.vue](../../../frontend/src/views/admin/ProposalsView.vue) 的 `entityTypeLabel` 映射对象（用 `grep -n "entityTypeLabel" frontend/src/views/admin/ProposalsView.vue` 定位）里补两条：

```javascript
  entity_unit_override: '实体单位覆盖',
  entity_density: '实体密度',
```

- [ ] **Step 4: 前端构建验证**

Run: `cd /d/code/live_calc/frontend && npm run build`
Expected: 构建成功，无 TypeScript / 编译错误。

---

## 完成验证（全任务结束后）

- [ ] 后端全量回归：`cd /d/code/live_calc/backend && python -m pytest tests/test_entity_executors.py tests/test_entity_unit_density_proposals.py tests/models/test_entity_soft_delete.py tests/test_shared_data.py tests/test_proposals_framework.py tests/test_permissions_p0.py -v`，全部 passed（失败数应不高于已知基线，且新测试全过）。
- [ ] grep 复核下游过滤无遗漏（Task 4 Step 7）。
- [ ] 前端 `npm run build` 通过。
- [ ] 开发库 `livecalc.db` 两表 `is_active` 列已落地（Task 1 Step 6）。
- [ ] 手动验收（已在运行的自动重载服务）：管理员维护自定义单位/密度即时生效；普通用户提交后详情页弹「待审核」、列表暂不显示待定值；审核台能看到 `实体单位覆盖`/`实体密度` 类型的待审提议，批准后数据出现。
