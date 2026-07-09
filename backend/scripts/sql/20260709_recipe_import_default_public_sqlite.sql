-- 菜谱发布默认私有（方案 A）：导入菜谱补 is_public=true
-- 一次性执行；已执行请跳过。纯数据 UPDATE，无表结构变更。
-- SQLite 布尔字面量用 1/0（boolean 即 integer 别名）。
UPDATE recipes SET is_public = 1
WHERE source IS NOT NULL AND source <> 'custom' AND is_public = 0;
