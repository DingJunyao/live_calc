-- 用户管理 & 邀请码增强
-- 引擎：PostgreSQL
-- 1) 新建 system_config 表（动态系统配置）
-- 2) invite_codes 表：used → used_count，新增 max_uses

-- ==================== system_config ====================

CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(100) PRIMARY KEY NOT NULL,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ==================== invite_codes 改造 ====================

ALTER TABLE invite_codes RENAME COLUMN used TO used_count;

ALTER TABLE invite_codes ADD COLUMN IF NOT EXISTS max_uses INTEGER;
