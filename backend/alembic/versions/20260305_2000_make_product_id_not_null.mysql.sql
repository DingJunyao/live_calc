-- MySQL 版本
-- 步骤1: 创建临时商品和食材，为没有 product_id 的记录提供默认值

-- 创建临时食材
INSERT IGNORE INTO ingredients (name, is_imported, created_by, updated_by, is_active, created_at, updated_at)
SELECT DISTINCT
    pr.product_name,
    1 as is_imported,
    pr.user_id as created_by,
    pr.user_id as updated_by,
    1 as is_active,
    NOW() as created_at,
    NOW() as updated_at
FROM product_records pr
WHERE pr.product_id IS NULL
AND NOT EXISTS (
    SELECT 1 FROM ingredients i WHERE i.name = pr.product_name AND i.is_active = 1
);

-- 创建临时商品
INSERT IGNORE INTO products (name, ingredient_id, created_by, updated_by, is_active, created_at, updated_at)
SELECT DISTINCT
    pr.product_name,
    i.id as ingredient_id,
    pr.user_id as created_by,
    pr.user_id as updated_by,
    1 as is_active,
    NOW() as created_at,
    NOW() as updated_at
FROM product_records pr
INNER JOIN ingredients i ON i.name = pr.product_name AND i.is_active = 1
WHERE pr.product_id IS NULL
AND NOT EXISTS (
    SELECT 1 FROM products p WHERE p.name = pr.product_name AND p.ingredient_id = i.id AND p.is_active = 1
);

-- 更新 product_id
UPDATE product_records pr
INNER JOIN products p ON p.name = pr.product_name
SET pr.product_id = p.id
WHERE pr.product_id IS NULL;

-- 步骤2: 修改列约束
ALTER TABLE product_records MODIFY COLUMN product_id INTEGER NOT NULL;

-- 步骤3: 添加外键约束
ALTER TABLE product_records
ADD CONSTRAINT fk_product_records_product_id
FOREIGN KEY (product_id) REFERENCES products(id)
ON DELETE CASCADE ON UPDATE CASCADE;
