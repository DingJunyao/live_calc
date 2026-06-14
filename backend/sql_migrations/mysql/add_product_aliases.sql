-- MySQL: 为 products 表添加 aliases 列
-- 使用 JSON 类型存储别名列表

ALTER TABLE products ADD COLUMN aliases JSON DEFAULT NULL COMMENT '别名列表，如["番茄","西红柿"]';
