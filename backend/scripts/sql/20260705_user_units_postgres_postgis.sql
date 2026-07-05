-- =====================================================================
-- 用户单位偏好（4 列） + 删除 ingredients.default_unit_id
-- 引擎：PostgreSQL（启用 PostGIS）
-- 日期：2026-07-05
--
-- 说明：本变更与 PostGIS 无关，SQL 与未启用 PostGIS 版本完全相同。
--   * users 加 4 列；3 个质量/容积/价格列内联 REFERENCES units(id) 自动建 FK。
--   * ingredients 删 default_unit_id：PostgreSQL 的 DROP COLUMN 会自动级联
--     删除该列上的索引（如 ix_ingredients_default_unit_id），无需手动处理。
--   * 执行前请备份。
-- =====================================================================

-- 1. users 加 4 列单位偏好（内联 FK）
ALTER TABLE users
  ADD COLUMN default_energy_unit VARCHAR(10),
  ADD COLUMN default_mass_unit_id INTEGER REFERENCES units(id),
  ADD COLUMN default_volume_unit_id INTEGER REFERENCES units(id),
  ADD COLUMN default_price_unit_id INTEGER REFERENCES units(id);

-- 2. ingredients 删 default_unit_id（索引自动级联删除）
ALTER TABLE ingredients DROP COLUMN default_unit_id;
