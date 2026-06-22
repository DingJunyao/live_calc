-- PostgreSQL: 给 users 加 token_version 列
-- 执行: psql -U root -d livecalc -f scripts/sql/20260622_add_token_version_to_users_postgresql.sql
ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0;
