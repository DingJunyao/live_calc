-- ============================================================
-- 为 ingredients 表新增 serving_weight + serving_weight_unit_id
-- 用途：半成品制作菜谱的成本换算（成品基准量）
-- 语义：servings 是基准量的倍数，成品总产量 = servings × serving_weight(折算为克)
-- 兼容：SQLite / MySQL / PostgreSQL
-- 日期：2026-06-15
-- ============================================================
-- 注意事项：
--   1. SQLite 的 ALTER TABLE 每条仅能新增一列，且不支持添加外键约束
--   2. MySQL / PostgreSQL 支持在一条 ALTER 中加多列并建立外键
--   3. 请按目标引擎选择下方对应段落执行
-- ============================================================

-- ============================================================
-- SQLite（开发库默认引擎）
-- ============================================================
ALTER TABLE ingredients ADD COLUMN serving_weight NUMERIC(10, 3);
ALTER TABLE ingredients ADD COLUMN serving_weight_unit_id INTEGER;
-- SQLite 不支持 ADD CONSTRAINT，外键关系仅在 ORM 层维护

-- ============================================================
-- MySQL
-- （执行前请确认两列尚未存在；如需回滚见文末）
-- ============================================================
-- ALTER TABLE ingredients
--   ADD COLUMN serving_weight DECIMAL(10, 3) NULL COMMENT '成品基准量（每份多重），用于制作菜谱成本换算',
--   ADD COLUMN serving_weight_unit_id INT NULL COMMENT '成品基准量单位ID',
--   ADD CONSTRAINT fk_ingredients_serving_weight_unit_id
--     FOREIGN KEY (serving_weight_unit_id) REFERENCES units (id);

-- ============================================================
-- PostgreSQL
-- ============================================================
-- ALTER TABLE ingredients
--   ADD COLUMN serving_weight NUMERIC(10, 3),
--   ADD COLUMN serving_weight_unit_id INTEGER,
--   ADD CONSTRAINT fk_ingredients_serving_weight_unit_id
--     FOREIGN KEY (serving_weight_unit_id) REFERENCES units (id);

-- ============================================================
-- 回滚（按引擎）
-- ============================================================
-- SQLite: 需重建表（SQLite < 3.35 不支持 DROP COLUMN），或使用 alembic batch 模式
-- MySQL:   ALTER TABLE ingredients DROP FOREIGN KEY fk_ingredients_serving_weight_unit_id;
--          ALTER TABLE ingredients DROP COLUMN serving_weight_unit_id, DROP COLUMN serving_weight;
-- PostgreSQL: ALTER TABLE ingredients
--               DROP CONSTRAINT fk_ingredients_serving_weight_unit_id,
--               DROP COLUMN serving_weight_unit_id,
--               DROP COLUMN serving_weight;
