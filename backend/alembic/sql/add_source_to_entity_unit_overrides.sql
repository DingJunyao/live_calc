-- ============================================================
-- entity_unit_overrides 新增 source 列
-- 版本: 20260605_0001
-- 日期: 2026-06-05
-- 说明: 添加 source 字段，区分自动导入(import)和手动维护(manual)
-- ============================================================


-- ============================================================
-- 一、SQLite 版本
-- ============================================================

ALTER TABLE entity_unit_overrides ADD COLUMN source VARCHAR(20) DEFAULT 'manual';


-- ============================================================
-- 二、MySQL 版本
-- ============================================================

-- ALTER TABLE entity_unit_overrides ADD COLUMN source VARCHAR(20) DEFAULT 'manual' AFTER is_default;


-- ============================================================
-- 三、PostgreSQL 版本（无 PostGIS）
-- ============================================================

-- ALTER TABLE entity_unit_overrides ADD COLUMN source VARCHAR(20) DEFAULT 'manual';


-- ============================================================
-- 回滚（仅 MySQL / PostgreSQL，SQLite 不支持 DROP COLUMN）
-- ============================================================

-- ALTER TABLE entity_unit_overrides DROP COLUMN source;
