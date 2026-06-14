-- PostgreSQL: 为 products 表添加 aliases 列
-- 使用 JSONB 类型存储别名列表（支持索引和高效查询）

ALTER TABLE products ADD COLUMN aliases JSONB DEFAULT NULL;
COMMENT ON COLUMN products.aliases IS '别名列表，如["番茄","西红柿"]';
