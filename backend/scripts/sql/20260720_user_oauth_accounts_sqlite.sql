-- user_oauth_accounts 表 — OAuth provider 框架预留（SQLite）
-- 适用于离线开发环境
-- 执行前备份 livecalc.db！

CREATE TABLE IF NOT EXISTS user_oauth_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    provider VARCHAR(32) NOT NULL,
    provider_user_id VARCHAR(128) NOT NULL,
    unionid VARCHAR(128),
    access_token VARCHAR(512),
    refresh_token VARCHAR(512),
    expires_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_provider_user ON user_oauth_accounts(provider, provider_user_id);
CREATE INDEX IF NOT EXISTS ix_oauth_unionid ON user_oauth_accounts(unionid);

-- 验证
-- PRAGMA table_info(user_oauth_accounts);
