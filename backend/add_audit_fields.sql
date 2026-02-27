-- 为数据库表添加审计字段和软删除功能

-- 添加审计字段到 ingredients 表
ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id);
ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES users(id);
ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE NOT NULL;

-- 添加审计字段到 ingredient_categories 表
ALTER TABLE ingredient_categories ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id);
ALTER TABLE ingredient_categories ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES users(id);
ALTER TABLE ingredient_categories ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE NOT NULL;

-- 添加审计字段到 ingredient_densities 表
ALTER TABLE ingredient_densities ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id);
ALTER TABLE ingredient_densities ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES users(id);
ALTER TABLE ingredient_densities ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE NOT NULL;

-- 添加审计字段到 ingredient_hierarchy 表
ALTER TABLE ingredient_hierarchy ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id);
ALTER TABLE ingredient_hierarchy ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES users(id);
ALTER TABLE ingredient_hierarchy ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE NOT NULL;

-- 添加审计字段到 units 表
ALTER TABLE units ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id);
ALTER TABLE units ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES users(id);
ALTER TABLE units ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE NOT NULL;

-- 添加审计字段到 unit_conversions 表
ALTER TABLE unit_conversions ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id);
ALTER TABLE unit_conversions ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES users(id);
ALTER TABLE unit_conversions ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE NOT NULL;

-- 为现有记录设置默认值
UPDATE ingredients SET is_active = TRUE WHERE is_active IS NULL;
UPDATE ingredient_categories SET is_active = TRUE WHERE is_active IS NULL;
UPDATE ingredient_densities SET is_active = TRUE WHERE is_active IS NULL;
UPDATE ingredient_hierarchy SET is_active = TRUE WHERE is_active IS NULL;
UPDATE units SET is_active = TRUE WHERE is_active IS NULL;
UPDATE unit_conversions SET is_active = TRUE WHERE is_active IS NULL;

-- 更新现有数据的created_at字段为NOT NULL（如果存在NULL值）
UPDATE ingredients SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL;
UPDATE ingredient_categories SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL;
UPDATE ingredient_densities SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL;
UPDATE ingredient_hierarchy SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL;
UPDATE units SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL;
UPDATE unit_conversions SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL;