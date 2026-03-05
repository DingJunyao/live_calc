-- SQLite 版本
ALTER TABLE product_records ADD COLUMN product_id_new INTEGER NOT NULL DEFAULT 0;
UPDATE product_records SET product_id_new = product_id WHERE product_id IS NOT NULL;
-- 处理 NULL 值：创建临时商品
-- 注意：需要先确保 ingredients 表中有对应的记录，如果没有需要先插入
-- 然后将临时商品 ID 分配给 product_id_new
-- 最后删除旧列并重命名新列
-- ALTER TABLE product_records DROP COLUMN product_id;
-- ALTER TABLE product_records RENAME COLUMN product_id_new TO product_id;
