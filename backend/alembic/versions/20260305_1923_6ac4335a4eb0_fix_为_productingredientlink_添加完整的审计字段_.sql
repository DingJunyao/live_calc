-- SQLite 版本
-- 为 product_ingredient_links 表添加完整的审计字段

-- 添加 created_by 列
ALTER TABLE product_ingredient_links ADD COLUMN created_by INTEGER;
ALTER TABLE product_ingredient_links ADD CONSTRAINT fk_product_ingredient_links_created_by
    FOREIGN KEY (created_by) REFERENCES users(id);

-- 添加 updated_by 列
ALTER TABLE product_ingredient_links ADD COLUMN updated_by INTEGER;
ALTER TABLE product_ingredient_links ADD CONSTRAINT fk_product_ingredient_links_updated_by
    FOREIGN KEY (updated_by) REFERENCES users(id);

-- 添加 is_active 列
ALTER TABLE product_ingredient_links ADD COLUMN is_active BOOLEAN DEFAULT 1 NOT NULL;

-- 确保 created_at 和 updated_at 有 NOT NULL 约束
-- 注意：SQLite 不支持直接修改列约束，如果表中已有数据，
-- 这个操作需要通过重建表来完成，详见 Python 迁移脚本
