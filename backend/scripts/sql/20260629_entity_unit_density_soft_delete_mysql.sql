-- 实体单位覆盖 + 实体密度 软删改造（MySQL）
-- MySQL 上 UNIQUE 约束为真实命名 uq_entity_unit / uq_entity_density（走命名索引），
-- 可直接 DROP INDEX。注意 MySQL DROP INDEX 语义即删唯一约束。

ALTER TABLE entity_unit_overrides
    ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
DROP INDEX uq_entity_unit ON entity_unit_overrides;
CREATE INDEX ix_entity_unit_active
    ON entity_unit_overrides(entity_type, entity_id, unit_name);
CREATE INDEX ix_entity_unit_overrides_is_active
    ON entity_unit_overrides(is_active);

ALTER TABLE entity_densities
    ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
DROP INDEX uq_entity_density ON entity_densities;
CREATE INDEX ix_entity_density_active
    ON entity_densities(entity_type, entity_id, condition);
CREATE INDEX ix_entity_densities_is_active
    ON entity_densities(is_active);
