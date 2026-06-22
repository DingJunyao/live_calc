-- 用户管理 & 邀请码增强
-- 引擎：MySQL
-- 1) 新建 system_config 表（动态系统配置）
-- 2) invite_codes 表：used → used_count，新增 max_uses

-- ==================== system_config ====================

CREATE TABLE IF NOT EXISTS system_config (
    `key` VARCHAR(100) PRIMARY KEY NOT NULL,
    value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 初始化默认配置（如数据库无记录则回退 .env 值）
INSERT IGNORE INTO system_config (`key`, value) VALUES ('registration_require_invite_code', 'false');

-- ==================== invite_codes 改造 ====================

ALTER TABLE invite_codes CHANGE COLUMN used used_count INT NOT NULL DEFAULT 0;

ALTER TABLE invite_codes ADD COLUMN max_uses INT NULL;
