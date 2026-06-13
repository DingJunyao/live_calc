-- 修复：删除原料后无法新建同名原料
-- 数据库：MySQL
-- 说明：将 ingredients.name 的唯一索引降级为普通索引，
--       使软删除(is_active=0)的原料不再占用 name，允许删除后新建同名原料。

DROP INDEX ix_ingredients_name ON ingredients;
CREATE INDEX ix_ingredients_name ON ingredients (name);
