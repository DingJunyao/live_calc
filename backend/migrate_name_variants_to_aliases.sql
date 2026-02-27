-- 数据库迁移脚本：将 name_variants 字段迁移为 aliases 字段
-- 适用于 SQLite

-- 步骤 1：添加新字段 aliases（如果不存在）
-- 注意：SQLite 不支持 IF NOT EXISTS 用于 ALTER TABLE ADD COLUMN
-- 请先检查字段是否存在，或直接运行（如果字段已存在会报错，可忽略）

ALTER TABLE ingredients ADD COLUMN aliases TEXT;

-- 步骤 2：数据迁移需要通过 Python 脚本处理 JSON 数据
-- 请运行：cd backend && python migrate_name_variants_to_aliases.py

-- 验证迁移结果的查询
SELECT id, name, aliases FROM ingredients WHERE aliases IS NOT NULL LIMIT 10;

-- 步骤 3（可选）：确认迁移成功后删除旧字段
-- SQLite 不支持 DROP COLUMN，需要重建表
-- 如需删除 name_variants 字段，请使用以下脚本：

/*
-- 备份原表
CREATE TABLE ingredients_backup AS SELECT * FROM ingredients;

-- 创建新表（不包含 name_variants 字段）
-- 注意：需要根据实际表结构调整字段列表
-- 此处仅为示例，请谨慎操作

-- 方案：保持字段，应用层忽略即可
*/