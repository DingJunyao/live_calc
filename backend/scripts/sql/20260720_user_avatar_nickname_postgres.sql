-- User 模型加 avatar/nickname 列（PostgreSQL）
-- avatar VARCHAR(500) — storage key（如 avatars/uuid.png），nullable
-- nickname VARCHAR(50) — 显示名，nullable，空时前端回退为 username
-- 执行前备份数据库！

ALTER TABLE users ADD COLUMN avatar VARCHAR(500);
ALTER TABLE users ADD COLUMN nickname VARCHAR(50);

-- 验证
-- \d users
