-- PostgreSQL with PostGIS 版本
-- 步骤1: 创建临时商品和食材，为没有 product_id 的记录提供默认值

-- 创建临时食材
INSERT INTO ingredients (name, is_imported, created_by, updated_by, is_active, created_at, updated_at)
SELECT DISTINCT
    pr.product_name,
    true as is_imported,
    pr.user_id as created_by,
    pr.user_id as updated_by,
    true as is_active,
    NOW() as created_at,
    NOW() as updated_at
FROM product_records pr
WHERE pr.product_id IS NULL
AND NOT EXISTS (
    SELECT 1 FROM ingredients i WHERE i.name = pr.product_name AND i.is_active = true
)
ON CONFLICT (name) DO NOTHING;

-- 创建临时商品
INSERT INTO products (name, ingredient_id, created_by, updated_by, is_active, created_at, updated_at)
SELECT DISTINCT
    pr.product_name,
    i.id as ingredient_id,
    pr.user_id as created_by,
    pr.user_id as updated_by,
    true as is_active,
    NOW() as created_at,
    NOW() as updated_at
FROM product_records pr
INNER JOIN ingredients i ON i.name = pr.product_name AND i.is_active = true
WHERE pr.product_id IS NULL
AND NOT EXISTS (
    SELECT 1 FROM products p WHERE p.name = pr.product_name AND p.ingredient_id = i.id AND p.is_active = true
)
ON CONFLICT DO NOTHING;

-- 更新 product_id
UPDATE product_records pr
SET product_id = p.id
FROM products p
WHERE p.name = pr.product_name AND pr.product_id IS NULL;

-- 步骤2: 修改列约束
ALTER TABLE product_records ALTER COLUMN product_id SET NOT NULL;

-- 步骤3: 添加外键约束（如果不存在）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'product_records_product_id_fkey'
    ) THEN
        ALTER TABLE product_records
        ADD CONSTRAINT product_records_product_id_fkey
        FOREIGN KEY (product_id) REFERENCES products(id)
        ON DELETE CASCADE ON UPDATE CASCADE;
    END IF;
END $$;
