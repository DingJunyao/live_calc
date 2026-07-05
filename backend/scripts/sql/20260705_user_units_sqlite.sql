-- =====================================================================
-- 用户单位偏好（4 列） + 删除 ingredients.default_unit_id
-- 引擎：SQLite
-- 日期：2026-07-05
--
-- 说明：
--   * users 加 4 列（default_energy_unit / default_mass_unit_id /
--     default_volume_unit_id / default_price_unit_id）。
--   * ingredients 删 default_unit_id：SQLite 不支持 DROP COLUMN（3.35 前）
--     且即使新版对带 FK/索引的列也不稳，这里用「建新表 → 复制 → 删旧 →
--     改名 → 重建索引」的标准表重建流程，列结构按 d:/code/live_calc
--     开发库实际 .schema 抄录（仅去掉 default_unit_id 及其 FK/索引）。
--   * 执行前请先备份：.backup livecalc.db livecalc.db.bak 或 copy。
-- =====================================================================

-- 1. users 加 4 列单位偏好（NULL 允许，存量用户保持 NULL 由前端 fallback）
ALTER TABLE users ADD COLUMN default_energy_unit VARCHAR(10);
ALTER TABLE users ADD COLUMN default_mass_unit_id INTEGER REFERENCES units(id);
ALTER TABLE users ADD COLUMN default_volume_unit_id INTEGER REFERENCES units(id);
ALTER TABLE users ADD COLUMN default_price_unit_id INTEGER REFERENCES units(id);

-- 2. ingredients 删 default_unit_id（表重建）
BEGIN TRANSACTION;

CREATE TABLE ingredients_new (
	id INTEGER NOT NULL,
	name VARCHAR(200) NOT NULL,
	category_id INTEGER,
	density NUMERIC(10, 6),
	aliases JSON,
	nutrition_id INTEGER,
	piece_weight NUMERIC(10, 3),
	piece_weight_unit_id INTEGER,
	is_imported BOOLEAN NOT NULL,
	is_merged BOOLEAN NOT NULL,
	merged_into_id INTEGER,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	created_by INTEGER,
	updated_by INTEGER,
	is_active BOOLEAN NOT NULL,
	serving_weight NUMERIC(10,3),
	serving_weight_unit_id INTEGER,
	ai_inferred BOOLEAN DEFAULT 0 NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(category_id) REFERENCES ingredient_categories (id),
	FOREIGN KEY(nutrition_id) REFERENCES nutrition_data (id),
	FOREIGN KEY(piece_weight_unit_id) REFERENCES units (id),
	FOREIGN KEY(merged_into_id) REFERENCES ingredients (id),
	FOREIGN KEY(created_by) REFERENCES users (id),
	FOREIGN KEY(updated_by) REFERENCES users (id)
);

-- 复制数据（不含 default_unit_id；列顺序按建表顺序对齐）
INSERT INTO ingredients_new (
	id, name, category_id, density, aliases, nutrition_id,
	piece_weight, piece_weight_unit_id, is_imported, is_merged, merged_into_id,
	created_at, updated_at, created_by, updated_by, is_active,
	serving_weight, serving_weight_unit_id, ai_inferred
)
SELECT
	id, name, category_id, density, aliases, nutrition_id,
	piece_weight, piece_weight_unit_id, is_imported, is_merged, merged_into_id,
	created_at, updated_at, created_by, updated_by, is_active,
	serving_weight, serving_weight_unit_id, ai_inferred
FROM ingredients;

DROP TABLE ingredients;
ALTER TABLE ingredients_new RENAME TO ingredients;

-- 重建既有索引（ix_ingredients_default_unit_id 随列删除不再重建）
CREATE INDEX ix_ingredients_id ON ingredients (id);
CREATE INDEX ix_ingredients_name ON ingredients (name);

COMMIT;
