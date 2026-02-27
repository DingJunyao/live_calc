-- 单独为缺少updated_at列的表添加该字段
-- 由于SQLite限制，我们需要逐一添加

-- 为ingredient_categories添加updated_at
PRAGMA foreign_keys=off;
ALTER TABLE ingredient_categories ADD COLUMN updated_at DATETIME;
UPDATE ingredient_categories SET updated_at = created_at WHERE updated_at IS NULL;

-- 为ingredient_densities添加updated_at
ALTER TABLE ingredient_densities ADD COLUMN updated_at DATETIME;
UPDATE ingredient_densities SET updated_at = created_at WHERE updated_at IS NULL;

-- 为ingredient_hierarchy添加updated_at
ALTER TABLE ingredient_hierarchy ADD COLUMN updated_at DATETIME;
UPDATE ingredient_hierarchy SET updated_at = created_at WHERE updated_at IS NULL;

-- 为units添加updated_at
ALTER TABLE units ADD COLUMN updated_at DATETIME;
UPDATE units SET updated_at = created_at WHERE updated_at IS NULL;

-- 为unit_conversions添加updated_at
ALTER TABLE unit_conversions ADD COLUMN updated_at DATETIME;
UPDATE unit_conversions SET updated_at = created_at WHERE updated_at IS NULL;

-- 为nutrition_data添加updated_at
ALTER TABLE nutrition_data ADD COLUMN updated_at DATETIME;
UPDATE nutrition_data SET updated_at = created_at WHERE updated_at IS NULL;

-- 为ingredient_nutrition_mapping添加updated_at
ALTER TABLE ingredient_nutrition_mapping ADD COLUMN updated_at DATETIME;
UPDATE ingredient_nutrition_mapping SET updated_at = created_at WHERE updated_at IS NULL;

PRAGMA foreign_keys=on;