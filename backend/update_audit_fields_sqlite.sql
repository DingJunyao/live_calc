-- 为数据库表添加完整的审计字段和软删除功能
PRAGMA foreign_keys=off;  -- 临时禁用外键约束

BEGIN TRANSACTION;

-- 为 ingredients 表添加审计字段
ALTER TABLE ingredients ADD COLUMN created_by INTEGER;
ALTER TABLE ingredients ADD COLUMN updated_by INTEGER;
ALTER TABLE ingredients ADD COLUMN is_active BOOLEAN DEFAULT 1;
ALTER TABLE ingredients ADD COLUMN updated_at DATETIME;

-- 为 ingredient_categories 表添加审计字段
ALTER TABLE ingredient_categories ADD COLUMN created_by INTEGER;
ALTER TABLE ingredient_categories ADD COLUMN updated_by INTEGER;
ALTER TABLE ingredient_categories ADD COLUMN is_active BOOLEAN DEFAULT 1;
ALTER TABLE ingredient_categories ADD COLUMN updated_at DATETIME;

-- 为 ingredient_densities 表添加审计字段
ALTER TABLE ingredient_densities ADD COLUMN created_by INTEGER;
ALTER TABLE ingredient_densities ADD COLUMN updated_by INTEGER;
ALTER TABLE ingredient_densities ADD COLUMN is_active BOOLEAN DEFAULT 1;
ALTER TABLE ingredient_densities ADD COLUMN updated_at DATETIME;

-- 为 ingredient_hierarchy 表添加审计字段
ALTER TABLE ingredient_hierarchy ADD COLUMN created_by INTEGER;
ALTER TABLE ingredient_hierarchy ADD COLUMN updated_by INTEGER;
ALTER TABLE ingredient_hierarchy ADD COLUMN is_active BOOLEAN DEFAULT 1;
ALTER TABLE ingredient_hierarchy ADD COLUMN updated_at DATETIME;

-- 为 units 表添加审计字段
ALTER TABLE units ADD COLUMN created_by INTEGER;
ALTER TABLE units ADD COLUMN updated_by INTEGER;
ALTER TABLE units ADD COLUMN is_active BOOLEAN DEFAULT 1;
ALTER TABLE units ADD COLUMN updated_at DATETIME;

-- 为 unit_conversions 表添加审计字段
ALTER TABLE unit_conversions ADD COLUMN created_by INTEGER;
ALTER TABLE unit_conversions ADD COLUMN updated_by INTEGER;
ALTER TABLE unit_conversions ADD COLUMN is_active BOOLEAN DEFAULT 1;
ALTER TABLE unit_conversions ADD COLUMN updated_at DATETIME;

-- 为 nutrition_data 表添加审计字段
ALTER TABLE nutrition_data ADD COLUMN created_by INTEGER;
ALTER TABLE nutrition_data ADD COLUMN updated_by INTEGER;
ALTER TABLE nutrition_data ADD COLUMN is_active BOOLEAN DEFAULT 1;
ALTER TABLE nutrition_data ADD COLUMN updated_at DATETIME;

-- 为 ingredient_nutrition_mapping 表添加审计字段
ALTER TABLE ingredient_nutrition_mapping ADD COLUMN created_by INTEGER;
ALTER TABLE ingredient_nutrition_mapping ADD COLUMN updated_by INTEGER;
ALTER TABLE ingredient_nutrition_mapping ADD COLUMN is_active BOOLEAN DEFAULT 1;
ALTER TABLE ingredient_nutrition_mapping ADD COLUMN updated_at DATETIME;

-- 更新所有现有记录的 is_active 字段为 true
UPDATE ingredients SET is_active = 1 WHERE is_active IS NULL;
UPDATE ingredient_categories SET is_active = 1 WHERE is_active IS NULL;
UPDATE ingredient_densities SET is_active = 1 WHERE is_active IS NULL;
UPDATE ingredient_hierarchy SET is_active = 1 WHERE is_active IS NULL;
UPDATE units SET is_active = 1 WHERE is_active IS NULL;
UPDATE unit_conversions SET is_active = 1 WHERE is_active IS NULL;
UPDATE nutrition_data SET is_active = 1 WHERE is_active IS NULL;
UPDATE ingredient_nutrition_mapping SET is_active = 1 WHERE is_active IS NULL;

-- 设置 updated_at 为与 created_at 相同的值
UPDATE ingredients SET updated_at = created_at WHERE updated_at IS NULL AND created_at IS NOT NULL;
UPDATE ingredient_categories SET updated_at = created_at WHERE updated_at IS NULL AND created_at IS NOT NULL;
UPDATE ingredient_densities SET updated_at = created_at WHERE updated_at IS NULL AND created_at IS NOT NULL;
UPDATE ingredient_hierarchy SET updated_at = created_at WHERE updated_at IS NULL AND created_at IS NOT NULL;
UPDATE units SET updated_at = created_at WHERE updated_at IS NULL AND created_at IS NOT NULL;
UPDATE unit_conversions SET updated_at = created_at WHERE updated_at IS NULL AND created_at IS NOT NULL;
UPDATE nutrition_data SET updated_at = created_at WHERE updated_at IS NULL AND created_at IS NOT NULL;
UPDATE ingredient_nutrition_mapping SET updated_at = created_at WHERE updated_at IS NULL AND created_at IS NOT NULL;

COMMIT;

PRAGMA foreign_keys=on;  -- 重新启用外键约束