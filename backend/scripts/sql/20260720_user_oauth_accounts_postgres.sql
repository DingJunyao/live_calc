-- user_oauth_accounts 表 — OAuth provider 框架预留（PostgreSQL）
-- 执行前备份数据库！

CREATE TABLE IF NOT EXISTS user_oauth_accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    provider VARCHAR(32) NOT NULL,
    provider_user_id VARCHAR(128) NOT NULL,
    unionid VARCHAR(128),
    access_token VARCHAR(512),
    refresh_token VARCHAR(512),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_provider_user ON user_oauth_accounts(provider, provider_user_id);
CREATE INDEX IF NOT EXISTS ix_oauth_unionid ON user_oauth_accounts(unionid);

-- 验证
-- \d user_oauth_accounts
