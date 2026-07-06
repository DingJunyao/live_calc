"""entity_unit_override and entity_density soft delete

Revision ID: c0e1d2f3a4b5
Revises: 20260627_0002
Create Date: 2026-06-29

为 entity_unit_overrides 与 entity_densities 两表加 is_active 软删字段，并把原
uq_entity_unit / uq_entity_density 唯一约束降级为普通复合索引，使软删后同名重建
不撞约束（应用层校验带 is_active=True 过滤，参照 ingredients 同名重建先例）。

跨引擎关键差异（实测 Alembic + SQLAlchemy 反射行为）：
- 原模型 ``UniqueConstraint(..., name="uq_entity_unit")``：
  - **MySQL / PostgreSQL**：约束为真实命名 ``uq_entity_unit`` / ``uq_entity_density``，
    ``batch_alter_table`` 下 ``drop_constraint("uq_entity_unit", type_="unique")`` 命中。
  - **SQLite**：table-level UNIQUE 落成匿名 ``sqlite_autoindex_<table>_1``（忽略 name），
    且 SQLite 禁止直接 DROP 关联 UNIQUE 的 autoindex。唯一可靠办法是重建表。
    经实测，``batch_alter_table`` 在两种上下文下 drop 唯一约束的行为不一致：
      * 直接 ``MigrationContext``：``naming_convention`` + ``drop_constraint`` 可命中；
      * 经 env.py（``context.configure(target_metadata=...)``）：新模型已无 UniqueConstraint，
        反射到的约束被归入「待删除」而非「命名保留」，``drop_constraint`` 抛 ValueError。
    故 SQLite 不依赖 drop_constraint，改用 ``op.execute`` 手写表重建（与
    scripts/sql/..._sqlite.sql 完全一致的 CREATE+INSERT+DROP+RENAME 流程），
    保留数据、主键、外键、时间戳默认值，并天然去掉匿名 UNIQUE。
"""
from alembic import op
import sqlalchemy as sa


revision = "c0e1d2f3a4b5"
down_revision = "20260627_0002"
branch_labels = None
depends_on = None


def _exec_sqlite_script(script):
    """逐条 op.execute（SQLAlchemy execute 不允许多语句脚本，按 ';' 拆分执行）。"""
    for stmt in script.split(";"):
        stmt = stmt.strip()
        if stmt:
            op.execute(stmt)


# ---------- SQLite：表重建 SQL（与 scripts/sql/..._sqlite.sql 同源）----------
_SQLITE_UPGRADE = """
CREATE TABLE _entity_unit_overrides_new (
    id INTEGER NOT NULL PRIMARY KEY,
    entity_type VARCHAR(20) NOT NULL,
    entity_id INTEGER NOT NULL,
    unit_name VARCHAR(50) NOT NULL,
    base_unit_id INTEGER REFERENCES units(id),
    conversion_factor NUMERIC(15, 10),
    weight_per_unit NUMERIC(10, 3),
    weight_unit_id INTEGER REFERENCES units(id),
    is_default BOOLEAN,
    source VARCHAR(20) DEFAULT 'manual',
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO _entity_unit_overrides_new
    (id, entity_type, entity_id, unit_name, base_unit_id, conversion_factor,
     weight_per_unit, weight_unit_id, is_default, source, is_active,
     created_at, updated_at)
SELECT id, entity_type, entity_id, unit_name, base_unit_id, conversion_factor,
       weight_per_unit, weight_unit_id, is_default, source, 1,
       created_at, updated_at
FROM entity_unit_overrides;
DROP TABLE entity_unit_overrides;
ALTER TABLE _entity_unit_overrides_new RENAME TO entity_unit_overrides;
CREATE INDEX ix_entity_unit_overrides_id ON entity_unit_overrides(id);

CREATE TABLE _entity_densities_new (
    id INTEGER NOT NULL PRIMARY KEY,
    entity_type VARCHAR(20) NOT NULL,
    entity_id INTEGER NOT NULL,
    density NUMERIC(10, 6) NOT NULL,
    temperature NUMERIC(5, 2),
    condition VARCHAR(100),
    source VARCHAR(200),
    confidence NUMERIC(3, 2) DEFAULT 1.0,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO _entity_densities_new
    (id, entity_type, entity_id, density, temperature, condition, source,
     confidence, is_active, created_at, updated_at)
SELECT id, entity_type, entity_id, density, temperature, condition, source,
       confidence, 1, created_at, updated_at
FROM entity_densities;
DROP TABLE entity_densities;
ALTER TABLE _entity_densities_new RENAME TO entity_densities;
CREATE INDEX ix_entity_densities_id ON entity_densities(id);
"""

_SQLITE_DOWNGRADE = """
CREATE TABLE _entity_unit_overrides_old (
    id INTEGER NOT NULL PRIMARY KEY,
    entity_type VARCHAR(20) NOT NULL,
    entity_id INTEGER NOT NULL,
    unit_name VARCHAR(50) NOT NULL,
    base_unit_id INTEGER REFERENCES units(id),
    conversion_factor NUMERIC(15, 10),
    weight_per_unit NUMERIC(10, 3),
    weight_unit_id INTEGER REFERENCES units(id),
    is_default BOOLEAN,
    source VARCHAR(20) DEFAULT 'manual',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (entity_type, entity_id, unit_name)
);
INSERT INTO _entity_unit_overrides_old
    (id, entity_type, entity_id, unit_name, base_unit_id, conversion_factor,
     weight_per_unit, weight_unit_id, is_default, source, created_at, updated_at)
SELECT id, entity_type, entity_id, unit_name, base_unit_id, conversion_factor,
       weight_per_unit, weight_unit_id, is_default, source, created_at, updated_at
FROM entity_unit_overrides;
DROP TABLE entity_unit_overrides;
ALTER TABLE _entity_unit_overrides_old RENAME TO entity_unit_overrides;
CREATE INDEX ix_entity_unit_overrides_id ON entity_unit_overrides(id);

CREATE TABLE _entity_densities_old (
    id INTEGER NOT NULL PRIMARY KEY,
    entity_type VARCHAR(20) NOT NULL,
    entity_id INTEGER NOT NULL,
    density NUMERIC(10, 6) NOT NULL,
    temperature NUMERIC(5, 2),
    condition VARCHAR(100),
    source VARCHAR(200),
    confidence NUMERIC(3, 2) DEFAULT 1.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (entity_type, entity_id, condition)
);
INSERT INTO _entity_densities_old
    (id, entity_type, entity_id, density, temperature, condition, source,
     confidence, created_at, updated_at)
SELECT id, entity_type, entity_id, density, temperature, condition, source,
       confidence, created_at, updated_at
FROM entity_densities;
DROP TABLE entity_densities;
ALTER TABLE _entity_densities_old RENAME TO entity_densities;
CREATE INDEX ix_entity_densities_id ON entity_densities(id);
"""


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        # 表重建：完整保留数据/主键/外键/时间戳，去掉匿名 UNIQUE（见模块 docstring）
        _exec_sqlite_script(_SQLITE_UPGRADE)
        op.create_index(
            "ix_entity_unit_active", "entity_unit_overrides",
            ["entity_type", "entity_id", "unit_name"], unique=False,
        )
        op.create_index(
            "ix_entity_unit_overrides_is_active", "entity_unit_overrides",
            ["is_active"], unique=False,
        )
        op.create_index(
            "ix_entity_density_active", "entity_densities",
            ["entity_type", "entity_id", "condition"], unique=False,
        )
        op.create_index(
            "ix_entity_densities_is_active", "entity_densities",
            ["is_active"], unique=False,
        )
    else:
        # MySQL / PostgreSQL：约束为真实命名，drop_constraint 命中
        with op.batch_alter_table("entity_unit_overrides") as batch_op:
            batch_op.add_column(
                sa.Column("is_active", sa.Boolean(), nullable=False,
                          server_default=sa.text("true"))
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

        with op.batch_alter_table("entity_densities") as batch_op:
            batch_op.add_column(
                sa.Column("is_active", sa.Boolean(), nullable=False,
                          server_default=sa.text("true"))
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
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        op.drop_index("ix_entity_densities_is_active", table_name="entity_densities")
        op.drop_index("ix_entity_density_active", table_name="entity_densities")
        op.drop_index("ix_entity_unit_overrides_is_active", table_name="entity_unit_overrides")
        op.drop_index("ix_entity_unit_active", table_name="entity_unit_overrides")
        # 表重建回滚：去掉 is_active，恢复匿名 UNIQUE
        _exec_sqlite_script(_SQLITE_DOWNGRADE)
    else:
        op.drop_index("ix_entity_densities_is_active", table_name="entity_densities")
        op.drop_index("ix_entity_density_active", table_name="entity_densities")
        with op.batch_alter_table("entity_densities") as batch_op:
            batch_op.create_unique_constraint(
                "uq_entity_density", ["entity_type", "entity_id", "condition"])
            batch_op.drop_column("is_active")

        op.drop_index("ix_entity_unit_overrides_is_active", table_name="entity_unit_overrides")
        op.drop_index("ix_entity_unit_active", table_name="entity_unit_overrides")
        with op.batch_alter_table("entity_unit_overrides") as batch_op:
            batch_op.create_unique_constraint(
                "uq_entity_unit", ["entity_type", "entity_id", "unit_name"])
            batch_op.drop_column("is_active")
