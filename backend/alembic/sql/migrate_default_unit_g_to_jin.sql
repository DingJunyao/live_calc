-- ============================================================
-- 迁移：将原料默认单位从「克(g)」改为「斤」
--
-- 适用数据库：SQLite / MySQL / PostgreSQL
-- 原理：通过 abbreviation 查找单位，避免硬编码 ID
-- ============================================================

-- SQLite
UPDATE ingredients
SET default_unit_id = (SELECT id FROM units WHERE abbreviation = '斤')
WHERE default_unit_id = (SELECT id FROM units WHERE abbreviation = 'g');

-- MySQL (同上，语法兼容)
-- UPDATE ingredients
-- SET default_unit_id = (SELECT id FROM units WHERE abbreviation = '斤')
-- WHERE default_unit_id = (SELECT id FROM units WHERE abbreviation = 'g');

-- PostgreSQL (同上，语法兼容)
-- UPDATE ingredients
-- SET default_unit_id = (SELECT id FROM units WHERE abbreviation = '斤')
-- WHERE default_unit_id = (SELECT id FROM units WHERE abbreviation = 'g');
