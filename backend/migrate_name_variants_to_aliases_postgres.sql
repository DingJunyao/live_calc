-- 数据库迁移脚本：将 name_variants 字段迁移为 aliases 字段
-- 适用于 PostgreSQL

-- 步骤 1：添加新字段 aliases（如果不存在）
ALTER TABLE ingredients
ADD COLUMN IF NOT EXISTS aliases JSONB DEFAULT '[]'::jsonb;

-- 步骤 2：数据迁移
-- 将 name_variants 中的 aliases 和 region_specific 合并到新的 aliases 字段

UPDATE ingredients
SET aliases = (
    SELECT jsonb_agg(DISTINCT val)
    FROM (
        -- 提取 aliases 数组中的值
        SELECT jsonb_array_elements_text(
            COALESCE(name_variants->'aliases', '[]'::jsonb)
        ) AS val
        WHERE name_variants->'aliases' IS NOT NULL

        UNION

        -- 提取 region_specific 中所有地区的别名
        SELECT jsonb_array_elements_text(
            COALESCE(name_variants->'region_specific'->key, '[]'::jsonb)
        ) AS val
        FROM jsonb_object_keys(
            COALESCE(name_variants->'region_specific', '{}'::jsonb)
        ) AS key
        WHERE name_variants->'region_specific' IS NOT NULL
    ) AS extracted
    WHERE val IS NOT NULL AND val != ''
)
WHERE name_variants IS NOT NULL
  AND (aliases IS NULL OR aliases = '[]'::jsonb);

-- 更新空的 aliases 为空数组
UPDATE ingredients
SET aliases = '[]'::jsonb
WHERE aliases IS NULL;

-- 步骤 3（可选）：确认迁移成功后删除旧字段
-- ALTER TABLE ingredients DROP COLUMN name_variants;

-- 验证迁移结果
SELECT id, name, aliases FROM ingredients WHERE aliases IS NOT NULL AND aliases != '[]'::jsonb LIMIT 10;