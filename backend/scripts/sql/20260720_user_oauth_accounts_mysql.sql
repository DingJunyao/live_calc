-- user_oauth_accounts 表 — OAuth provider 框架预留（MySQL）
-- 执行前备份数据库！

CREATE TABLE IF NOT EXISTS user_oauth_accounts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    provider VARCHAR(32) NOT NULL,
    provider_user_id VARCHAR(128) NOT NULL,
    unionid VARCHAR(128),
    access_token VARCHAR(512),
    refresh_token VARCHAR(512),
    expires_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_provider_user (provider, provider_user_id),
    INDEX ix_oauth_unionid (unionid),
    CONSTRAINT fk_oauth_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 验证
-- DESCRIBE user_oauth_accounts;
