-- 图片路径剥前缀成 key（SQLite）
-- 迁移后 DB 只存 key（relative path），切 storage backend 时 DB 零改动
-- 外链 http(s):// 和已为 key（不以 / 开头）的路径不动
-- 执行前备份 livecalc.db！

-- recipes.images 是 JSON 数组 TEXT，REPLACE 纯文本替换安全
UPDATE recipes SET images = REPLACE(images, '/static/images/', '');

-- products.image_url 只处理带前缀的本地路径
UPDATE products SET image_url = REPLACE(image_url, '/static/images/', '')
WHERE image_url LIKE '/static/images/%';

-- 验证：以下两条应均空
-- SELECT images FROM recipes WHERE images LIKE '%/static/%';
-- SELECT image_url FROM products WHERE image_url LIKE '/static/%';
