-- ============================================================
-- 迁移：将所有原料的默认单位改为「斤」
--
-- 背景：之前仅将 g 改为 斤，但仍有大量食材的默认单位为
--       mL、个、片、只等非斤单位。本次将所有食材统一设为斤。
--
-- 适用数据库：SQLite / MySQL / PostgreSQL
-- 原理：通过 abbreviation 查找单位，避免硬编码 ID
-- ============================================================

-- SQLite
UPDATE ingredients
SET default_unit_id = (SELECT id FROM units WHERE abbreviation = '斤')
WHERE default_unit_id IS NOT NULL
  AND default_unit_id != (SELECT id FROM units WHERE abbreviation = '斤');

-- MySQL (语法兼容)
-- UPDATE ingredients
-- SET default_unit_id = (SELECT id FROM units WHERE abbreviation = '斤')
-- WHERE default_unit_id IS NOT NULL
--   AND default_unit_id != (SELECT id FROM units WHERE abbreviation = '斤');

-- PostgreSQL (语法兼容)
-- UPDATE ingredients
-- SET default_unit_id = (SELECT id FROM units WHERE abbreviation = '斤')
-- WHERE default_unit_id IS NOT NULL
--   AND default_unit_id != (SELECT id FROM units WHERE abbreviation = '斤');
