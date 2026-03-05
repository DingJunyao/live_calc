-- MySQL 版本
-- 为 product_ingredient_links 表添加完整的审计字段

-- 添加 created_by 列
ALTER TABLE product_ingredient_links
    ADD COLUMN created_by INTEGER NULL,
    ADD CONSTRAINT fk_product_ingredient_links_created_by
        FOREIGN KEY (created_by) REFERENCES users(id);

-- 添加 updated_by 列
ALTER TABLE product_ingredient_links
    ADD COLUMN updated_by INTEGER NULL,
    ADD CONSTRAINT fk_product_ingredient_links_updated_by
        FOREIGN KEY (updated_by) REFERENCES users(id);

-- 添加 is_active 列
ALTER TABLE product_ingredient_links
    ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL;

-- 确保 created_at 和 updated_at 有 NOT NULL 约束（如果还没有的话）
ALTER TABLE product_ingredient_links
    MODIFY COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL;
ALTER TABLE product_ingredient_links
    MODIFY COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL;

-- 回滚脚本
/*
ALTER TABLE product_ingredient_links DROP FOREIGN KEY fk_product_ingredient_links_created_by;
ALTER TABLE product_ingredient_links DROP FOREIGN KEY fk_product_ingredient_links_updated_by;
ALTER TABLE product_ingredient_links DROP COLUMN created_by;
ALTER TABLE product_ingredient_links DROP COLUMN updated_by;
ALTER TABLE product_ingredient_links DROP COLUMN is_active;
*/
