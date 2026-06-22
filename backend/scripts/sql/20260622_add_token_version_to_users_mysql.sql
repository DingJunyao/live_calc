-- MySQL: 给 users 加 token_version 列
-- 执行: mysql -u root -p livecalc < scripts/sql/20260622_add_token_version_to_users_mysql.sql
ALTER TABLE users ADD COLUMN token_version INT NOT NULL DEFAULT 0;
