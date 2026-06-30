-- 实体单位覆盖 + 实体密度 软删改造（SQLite）
--
-- 关键差异：原模型用 UniqueConstraint(name="uq_entity_unit")，但 SQLite 建表时
-- 把 table-level UNIQUE 落成匿名 sqlite_autoindex_<table>_1（忽略 name），且 SQLite
-- 禁止直接 DROP 关联 UNIQUE 约束的 autoindex。唯一可行办法是「重建表去 UNIQUE」。
-- 故两表都用 CREATE 新表(无 UNIQUE，普通复合索引) + INSERT 复制 + DROP 旧表 + RENAME
-- 的标准表重建流程，完整保留数据、主键、外键(entity_unit_overrides 的 base_unit_id/
-- weight_unit_id -> units.id)与 created_at/updated_at 默认值。
-- 重建后追加 is_active 列与两表各两个索引。
--
-- 注意：非幂等。表重建流程本身是一次性的，重复执行会因 DROP 旧表而报错。
-- 仅执行一次。

BEGIN;

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
CREATE INDEX ix_entity_unit_active
    ON entity_unit_overrides(entity_type, entity_id, unit_name);
CREATE INDEX ix_entity_unit_overrides_is_active
    ON entity_unit_overrides(is_active);

-- ===== entity_densities =====
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
CREATE INDEX ix_entity_density_active
    ON entity_densities(entity_type, entity_id, condition);
CREATE INDEX ix_entity_densities_is_active
    ON entity_densities(is_active);

COMMIT;
