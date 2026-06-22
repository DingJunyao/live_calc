-- 用户管理 & 邀请码增强
-- 引擎：SQLite
-- 1) 新建 system_config 表（动态系统配置）
-- 2) invite_codes 表：used → used_count，新增 max_uses

-- ==================== system_config ====================

CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(100) PRIMARY KEY NOT NULL,
    value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ==================== invite_codes 改造 ====================

-- SQLite 3.25+ 支持 RENAME COLUMN；若版本较老可手动迁移
ALTER TABLE invite_codes RENAME COLUMN used TO used_count;

-- 添加 max_uses 列（NULL = 不限次数）
-- SQLite 的 ADD COLUMN 不支持 IF NOT EXISTS，若列已存在会报错，请按实际情况处理
ALTER TABLE invite_codes ADD COLUMN max_uses INTEGER;
