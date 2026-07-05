-- =====================================================================
-- 用户单位偏好（4 列） + 删除 ingredients.default_unit_id
-- 引擎：MySQL
-- 日期：2026-07-05
--
-- 说明：
--   * users 加 4 列 + 3 个 FK（default_energy_unit 无 FK，是字符串枚举）。
--   * ingredients 删 default_unit_id：若该列上存在外键约束（名为
--     fk_ingredients_default_unit_id 或 alembic 自动生成名），需先
--     `ALTER TABLE ingredients DROP FOREIGN KEY <fk_name>;` 再 DROP COLUMN。
--     可用以下查询找出 FK 名：
--       SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE
--       WHERE TABLE_NAME='ingredients' AND COLUMN_NAME='default_unit_id'
--         AND TABLE_SCHEMA=DATABASE();
--   * 执行前请备份。
-- =====================================================================

-- 1. users 加 4 列单位偏好 + 3 个 FK
ALTER TABLE users
  ADD COLUMN default_energy_unit VARCHAR(10) NULL,
  ADD COLUMN default_mass_unit_id INT NULL,
  ADD COLUMN default_volume_unit_id INT NULL,
  ADD COLUMN default_price_unit_id INT NULL,
  ADD CONSTRAINT fk_users_default_mass_unit
    FOREIGN KEY (default_mass_unit_id) REFERENCES units(id),
  ADD CONSTRAINT fk_users_default_volume_unit
    FOREIGN KEY (default_volume_unit_id) REFERENCES units(id),
  ADD CONSTRAINT fk_users_default_price_unit
    FOREIGN KEY (default_price_unit_id) REFERENCES units(id);

-- 2. ingredients 删 default_unit_id（若列上有 FK，先 DROP FOREIGN KEY）
ALTER TABLE ingredients DROP COLUMN default_unit_id;
