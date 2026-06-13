-- 修复：删除原料后无法新建同名原料
-- 数据库：PostgreSQL
-- 说明：将 ingredients.name 的唯一索引降级为普通索引，
--       使软删除(is_active=false)的原料不再占用 name，允许删除后新建同名原料。

DROP INDEX IF EXISTS ix_ingredients_name;
CREATE INDEX ix_ingredients_name ON ingredients (name);
