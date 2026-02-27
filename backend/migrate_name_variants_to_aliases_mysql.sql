-- 数据库迁移脚本：将 name_variants 字段迁移为 aliases 字段
-- 适用于 MySQL

-- 步骤 1：添加新字段 aliases（如果不存在）
ALTER TABLE ingredients
ADD COLUMN IF NOT EXISTS aliases JSON;

-- 步骤 2：数据迁移
-- 将 name_variants 中的 aliases 和 region_specific 合并到新的 aliases 字段

UPDATE ingredients
SET aliases = JSON_MERGE_PRESERVE(
    COALESCE(JSON_EXTRACT(name_variants, '$.aliases'), '[]'),
    COALESCE(
        (
            SELECT JSON_ARRAYAGG(val)
            FROM JSON_TABLE(
                JSON_EXTRACT(name_variants, '$.region_specific'),
                '$.*' COLUMNS(val VARCHAR(255) PATH '$')
            ) AS jt
            WHERE val IS NOT NULL
        ),
        '[]'
    )
)
WHERE name_variants IS NOT NULL
  AND aliases IS NULL;

-- 对于 name_variants 中只有 aliases 的情况
UPDATE ingredients
SET aliases = JSON_EXTRACT(name_variants, '$.aliases')
WHERE name_variants IS NOT NULL
  AND JSON_TYPE(name_variants) = 'OBJECT'
  AND JSON_CONTAINS_PATH(name_variants, 'one', '$.aliases')
  AND aliases IS NULL;

-- 步骤 3（可选）：确认迁移成功后删除旧字段
-- ALTER TABLE ingredients DROP COLUMN name_variants;

-- 验证迁移结果
SELECT id, name, aliases FROM ingredients WHERE aliases IS NOT NULL LIMIT 10;