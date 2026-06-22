-- SQLite: 给 users 加 token_version 列（重置密码作废旧 token 用）
-- 执行: sqlite3 data/livecalc.db < scripts/sql/20260622_add_token_version_to_users_sqlite.sql
ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0;
