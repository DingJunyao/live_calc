-- SQLite: 为 products 表添加 aliases 列
-- JSON 数据在 SQLite 中以 TEXT 类型存储

ALTER TABLE products ADD COLUMN aliases TEXT;
