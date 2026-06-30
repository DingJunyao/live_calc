-- 实体单位覆盖 + 实体密度 软删改造（PostgreSQL）
-- PG 上 UNIQUE 约束为真实命名 uq_entity_unit / uq_entity_density，
-- 用 DROP CONSTRAINT 删除（PG 的唯一约束与索引分离，删约束即可）。

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
