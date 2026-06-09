-- ============================================================
-- merchants 新增 is_open 列
-- 版本: 20260609_0001
-- 日期: 2026-06-09
-- 说明: 添加 is_open 字段，标记商家是否营业（默认 true）
-- ============================================================


-- ============================================================
-- 一、SQLite 版本
-- ============================================================

ALTER TABLE merchants ADD COLUMN is_open BOOLEAN DEFAULT 1;
UPDATE merchants SET is_open = 1 WHERE is_open IS NULL;


-- ============================================================
-- 二、MySQL 版本
-- ============================================================

-- ALTER TABLE merchants ADD COLUMN is_open TINYINT(1) DEFAULT 1;
-- UPDATE merchants SET is_open = 1 WHERE is_open IS NULL;


-- ============================================================
-- 三、PostgreSQL 版本（无 PostGIS）
-- ============================================================

-- ALTER TABLE merchants ADD COLUMN is_open BOOLEAN DEFAULT true;
-- UPDATE merchants SET is_open = true WHERE is_open IS NULL;


-- ============================================================
-- 回滚（仅 MySQL / PostgreSQL，SQLite 不支持 DROP COLUMN）
-- ============================================================

-- ALTER TABLE merchants DROP COLUMN is_open;
