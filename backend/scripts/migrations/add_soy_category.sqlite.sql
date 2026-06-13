-- 新增「豆制品」食材分类，放在乳制品之后
-- 数据库：SQLite
-- 说明：在乳制品(sort_order=7)之后插入豆制品(sort_order=8)，
--       原 sort_order>=8 的分类（调味品、油脂、坚果、饮品）顺延。

-- 先检查是否已存在，避免重复执行
INSERT OR IGNORE INTO ingredient_categories (name, display_name, description, sort_order, is_active, created_at, updated_at)
SELECT 'soy', '豆制品', '豆腐、豆浆、豆皮、腐竹等', 8, 1, datetime('now'), datetime('now')
WHERE NOT EXISTS (SELECT 1 FROM ingredient_categories WHERE name = 'soy');

-- 更新已有分类的排序（仅在新增成功后才需要顺延）
-- 排除 sort_order >= 90 的末位分类（如「其他」），保持其固定在末尾
UPDATE ingredient_categories
SET sort_order = sort_order + 1
WHERE sort_order >= 8 AND sort_order < 90
  AND name != 'soy'
  AND EXISTS (SELECT 1 FROM ingredient_categories WHERE name = 'soy' AND sort_order = 8);
