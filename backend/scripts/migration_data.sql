-- ============================================================
-- 数据迁移 SQL 脚本
-- 生成时间: 2026-06-05
-- 源数据库: livecalc_bak.db (旧版本)
-- 目标数据库: livecalc.db (新版本)
-- ============================================================
-- 兼容: SQLite / MySQL / PostgreSQL
-- 注意事项:
--   1. MySQL 需要 LAST_INSERT_ID() 获取自增ID
--   2. PostgreSQL 需要 RETURNING id 或使用 SEQUENCE
--   3. 字段名使用下划线命名法（snake_case），需确认目标表结构一致
--   4. 日期格式为 ISO 8601 字符串
-- ============================================================

-- ============================================================
-- 1. 用户
-- ============================================================
INSERT INTO users (username, email, password_hash, is_admin, is_active, email_verified, created_at)
VALUES ('billding', 'dingjunyao0703@163.com', '$2b$12$FUjfp3qhiBWX4lfbJMJa4.dPVOXYwFOOiUv2cvODePnUvPsztbsXa', 1, 1, 0, '2026-03-12 16:50:39');

-- 新用户 ID = 1

-- ============================================================
-- 2. 商家
-- ============================================================
-- 旧ID=1, 新ID=1
INSERT INTO merchants (user_id, name, address, latitude, longitude, created_at, updated_at)
VALUES (1, '美道家梦之城店', '测试', 34.77900187229076, 111.19495116168976, '2026-03-12 02:03:16', '2026-03-18 17:01:40');

-- 旧ID=2, 新ID=2
INSERT INTO merchants (user_id, name, address, latitude, longitude, created_at, updated_at)
VALUES (1, '千禧量贩', '测试', 34.780296733482245, 111.1978232076279, '2026-03-13 12:21:35', '2026-03-18 17:02:07');

-- 旧ID=3, 新ID=3
INSERT INTO merchants (user_id, name, address, latitude, longitude, created_at, updated_at)
VALUES (1, '丹尼斯', '测试', 34.780160211226, 111.19313706048071, '2026-03-13 12:22:23', '2026-03-18 17:02:26');

-- 旧ID=5, 新ID=4
INSERT INTO merchants (user_id, name, address, latitude, longitude, created_at, updated_at)
VALUES (1, '美道家万达广场店', '测试', 34.78524584771957, 111.18352353572847, '2026-03-15 08:20:27', '2026-03-18 17:02:44');

-- ============================================================
-- 3. 新建原料（旧库商品无法匹配新库原料时创建）
-- ============================================================
-- 新建原料 ID=641
INSERT INTO ingredients (name, category_id, is_imported, is_merged, created_at, updated_at, is_active)
VALUES ('干燕麦片', 1, 0, 0, '2026-06-05 06:55:00', '2026-06-05 06:55:00', 1);

-- 新建原料 ID=642
INSERT INTO ingredients (name, category_id, is_imported, is_merged, created_at, updated_at, is_active)
VALUES ('鲜鸭血', 1, 0, 0, '2026-06-05 06:55:00', '2026-06-05 06:55:00', 1);

-- ============================================================
-- 4. 新建商品（旧库商品无法匹配新库商品时创建）
-- ============================================================
-- 新建商品 ID=619: 干燕麦片
INSERT INTO products (name, ingredient_id, created_at, updated_at, is_active)
VALUES ('干燕麦片', 641, '2026-06-05 06:55:00', '2026-06-05 06:55:00', 1);

-- 新建商品 ID=620: 鲜鸭血
INSERT INTO products (name, ingredient_id, created_at, updated_at, is_active)
VALUES ('鲜鸭血', 642, '2026-06-05 06:55:00', '2026-06-05 06:55:00', 1);

-- ============================================================
-- 5. 价格记录
-- ============================================================
-- 共 475 条

-- --- 批次 1 (记录 1-100) ---
INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 325, '尖椒', 1, 5.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:25:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 78, '黄瓜', 1, 4.38, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:27:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 1, '西葫芦', 1, 2.18, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:28:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 30, '娃娃菜', 1, 2.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:28:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 145, '包菜', 1, 1.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:30:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 320, '大白菜', 1, 1.18, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:30:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 481, '苦瓜', 1, 5.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:31:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 97, '胡萝卜', 1, 2.08, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:32:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 382, '莲藕', 1, 3.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:33:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 67, '生菜', 1, 1.78, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:33:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 63, '青菜', 1, 1.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:34:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 575, '菠菜', 1, 1.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:34:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 258, '油麦菜', 1, 3.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:35:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 277, '空心菜', 1, 5.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:36:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 65, '洋葱', 1, 1.68, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:36:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 103, '大葱', 1, 1.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:37:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 185, '芹菜', 1, 1.28, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:37:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 161, '蒜苗', 1, 2.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:38:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 121, '小香葱', 1, 3.58, 'CNY', 1, 7, 500, 3, 'purchase', 1, '2026-03-12 02:38:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 232, '香芹', 1, 2.48, 'CNY', 1, 7, 500, 3, 'purchase', 1, '2026-03-12 02:38:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 410, '韭菜', 1, 2.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:39:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 235, '小茴香', 1, 5.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:39:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 272, '薄荷叶', 1, 9.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:40:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 100, '咸鸭蛋', 1, 10, 'CNY', 8, 18, 8, 18, 'price', 1, '2026-03-12 02:41:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 79, '皮蛋', 1, 10, 'CNY', 15, 18, 15, 18, 'price', 1, '2026-03-12 02:42:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 119, '番茄', 1, 1.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:42:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 556, '西蓝花', 1, 2.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:42:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 129, '花菜', 1, 2.68, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:43:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 614, '蒜苔', 1, 5.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:43:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 562, '耙耙柑', 1, 4.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:44:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 136, '豆角', 1, 4.68, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:44:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 505, '腊肉', 1, 25.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:45:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 317, '腊肠', 1, 19.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:46:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 157, '河粉', 1, 3.9, 'CNY', 220, 3, 220, 3, 'price', 1, '2026-03-12 02:47:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 486, '千张', 1, 11.96, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-12 02:48:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 287, '干豆腐', 1, 13.96, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-12 02:49:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 324, '老豆腐', 1, 5.16, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-12 02:50:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 149, '豆腐', 1, 4.76, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-12 02:50:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 407, '内酯豆腐', 1, 1.99, 'CNY', 350, 3, 350, 3, 'price', 1, '2026-03-12 02:50:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 62, '鲜面条', 1, 2.68, 'CNY', 400, 3, 400, 3, 'price', 1, '2026-03-12 02:51:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 64, '豆芽', 1, 1.08, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:52:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 2, '鸡蛋', 1, 18.8, 'CNY', 30, 18, 30, 18, 'price', 1, '2026-03-12 02:53:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 339, '猪前肘', 1, 8.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:54:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 74, '猪五花肉', 1, 12.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:54:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 75, '里脊肉', 1, 9.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:55:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 377, '梅头猪肉', 1, 12.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:55:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 50, '猪瘦肉', 1, 12.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:56:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 44, '排骨', 1, 18.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:56:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 118, '牛肉', 1, 39.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:56:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 113, '羊排', 1, 32.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:57:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 102, '羊肉', 1, 39.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:57:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 275, '鸡腿', 1, 6.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:58:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 516, '鸡翅中', 1, 29.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:58:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 39, '鸡胸肉', 1, 7.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:59:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 585, '手枪腿（或者鸡胸脯肉）', 1, 7.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 02:59:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 328, '牛腱子', 1, 62.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 03:00:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 307, '牛腩', 1, 69.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 03:01:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 81, '牛奶', 9.9, 'CNY', 950, 3, 950, 3, 'purchase', 1, '2026-03-12 03:02:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 376, '橄榄油', 1, 118, 'CNY', 1.8, 4, 1800, 5, 'price', 1, '2026-03-12 03:05:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 86, '花生油', 1, 99.9, 'CNY', 5, 4, 5000, 5, 'price', 1, '2026-03-12 03:05:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 508, '紫菜', 1, 9.9, 'CNY', 60, 3, 60, 3, 'price', 1, '2026-03-12 03:06:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 331, '木耳（干）', 1, 28.9, 'CNY', 150, 3, 150, 3, 'price', 1, '2026-03-12 03:07:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 109, '枸杞', 1, 10.8, 'CNY', 50, 3, 50, 3, 'price', 1, '2026-03-12 03:07:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 301, '桂圆干', 1, 15, 'CNY', 200, 3, 200, 3, 'price', 1, '2026-03-12 03:07:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 146, '粉丝', 1, 13.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 03:08:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 352, '熟豆油', 1, 69.8, 'CNY', 5, 4, 5000, 5, 'price', 1, '2026-03-12 03:08:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 3, '食用油', 1, 65.8, 'CNY', 5, 4, 5000, 5, 'price', 1, '2026-03-12 03:09:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 22, '鸡精', 1, 10.8, 'CNY', 180, 3, 180, 3, 'price', 1, '2026-03-12 03:10:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 4, '盐', 1, 1, 'CNY', 400, 3, 400, 3, 'price', 1, '2026-03-12 03:11:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 21, '味精', 1, 6.2, 'CNY', 250, 3, 250, 3, 'price', 1, '2026-03-12 03:11:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 140, '玉米淀粉', 1, 2.9, 'CNY', 200, 3, 200, 3, 'price', 1, '2026-03-12 03:12:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 16, '红薯淀粉', 1, 5.5, 'CNY', 200, 3, 200, 3, 'price', 1, '2026-03-12 03:12:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 112, '土豆淀粉', 1, 5.5, 'CNY', 200, 3, 200, 3, 'price', 1, '2026-03-12 03:12:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 458, '豌豆淀粉', 1, 10.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 03:13:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 454, '小苏打', 1, 2.9, 'CNY', 250, 3, 250, 3, 'price', 1, '2026-03-12 03:13:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 192, '安琪干酵母粉', 1, 1.3, 'CNY', 13, 3, 13, 3, 'price', 1, '2026-03-12 03:14:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 70, '糯米粉', 1, 10.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 03:14:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 485, '火锅底料', 1, 17.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-12 03:14:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 147, '菜籽油', 1, 69, 'CNY', 5, 4, 5000, 5, 'price', 1, '2026-03-12 03:15:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 142, '大米', 1, 39, 'CNY', 5, 2, 5000, 3, 'price', 1, '2026-03-12 03:23:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 15, '普通面粉', 1, 25.8, 'CNY', 5, 2, 5000, 3, 'price', 1, '2026-03-12 03:24:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 145, '包菜', 1, 1.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:35:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 320, '大白菜', 1, 1.28, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:36:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 30, '娃娃菜', 1, 2.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:37:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 481, '苦瓜', 1, 5.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:37:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 1, '西葫芦', 1, 2.18, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:37:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 78, '黄瓜', 1, 3.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:38:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 562, '耙耙柑', 1, 4.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:38:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 325, '尖椒', 1, 5.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:38:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 136, '豆角', 1, 4.68, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:39:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 614, '蒜苔', 1, 4.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:39:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 129, '花菜', 1, 2.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:40:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 276, '西兰花', 1, 2.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:40:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 248, '香菇', 1, 8.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:40:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 119, '番茄', 1, 1.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:41:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 79, '皮蛋', 1, 10, 'CNY', 15, 18, 15, 18, 'price', 1, '2026-03-13 12:42:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 100, '咸鸭蛋', 1, 10, 'CNY', 8, 18, 8, 18, 'price', 1, '2026-03-13 12:42:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 97, '胡萝卜', 1, 1.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:43:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 382, '莲藕', 1, 3.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:43:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 87, '土豆', 1, 2.38, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:43:00.000000');

-- --- 批次 2 (记录 101-200) ---
INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 67, '生菜', 1, 1.78, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:44:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 63, '青菜', 1, 1.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:44:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 246, '冬笋', 1, 5.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:45:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 272, '薄荷叶', 1, 9.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:45:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 575, '菠菜', 1, 1.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:46:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 258, '油麦菜', 1, 3.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:46:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 277, '空心菜', 1, 6.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:46:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 65, '洋葱', 1, 1.68, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:47:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 28, '蒜', 1, 3.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:48:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 103, '大葱', 1, 1.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:49:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 185, '芹菜', 1, 1.28, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:49:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 232, '香芹', 1, 2.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:50:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 505, '腊肉', 1, 19.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:50:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 2, '鸡蛋', 1, 18.8, 'CNY', 30, 18, 30, 18, 'price', 1, '2026-03-13 12:50:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 275, '鸡腿', 1, 6.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:51:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 282, '鸡爪', 1, 19.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:51:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 516, '鸡翅中', 1, 29.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:52:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 39, '鸡胸肉', 1, 7.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:52:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 585, '手枪腿（或者鸡胸脯肉）', 1, 5.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:52:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 75, '里脊肉', 1, 15.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:53:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 339, '猪前肘', 1, 8.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:53:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 74, '五花肉', 1, 15.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:54:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 118, '牛肉', 1, 35.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:54:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 113, '羊排', 1, 32.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-13 12:54:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 10, '料酒', 1, 9.9, 'CNY', 1.75, 4, 1750, 5, 'purchase', 1, '2026-03-13 12:57:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 41, '香醋', 1, 10.9, 'CNY', 2, 4, 2000, 5, 'price', 1, '2026-03-13 12:57:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 24, '生抽', 1, 9.9, 'CNY', 1.28, 4, 1280, 5, 'price', 1, '2026-03-13 12:58:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 266, '陈醋', 1, 10.9, 'CNY', 2.5, 4, 2500, 5, 'price', 1, '2026-03-13 12:58:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 93, '米醋', 1, 10.9, 'CNY', 2.5, 4, 2500, 5, 'price', 1, '2026-03-13 12:58:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 31, '老抽', 1, 9.9, 'CNY', 1.25, 4, 1250, 5, 'price', 1, '2026-03-13 12:59:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 391, '挂面', 1, 3.9, 'CNY', 900, 3, 900, 3, 'price', 1, '2026-03-13 12:59:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 46, '蚝油', 1, 9.9, 'CNY', 815, 3, 815, 3, 'price', 1, '2026-03-13 13:00:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 580, '郫县豆瓣酱', 1, 12.8, 'CNY', 1, 2, 1000, 3, 'purchase', 1, '2026-03-13 13:02:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 68, '豆瓣酱', 1, 12.5, 'CNY', 800, 3, 800, 3, 'price', 1, '2026-03-13 13:02:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 58, '黄豆酱', 1, 13.9, 'CNY', 800, 3, 800, 3, 'price', 1, '2026-03-13 13:03:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 7, '甜面酱', 1, 12.8, 'CNY', 800, 3, 800, 3, 'price', 1, '2026-03-13 13:03:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 89, '油泼辣子', 1, 10.8, 'CNY', 248, 3, 248, 3, 'price', 1, '2026-03-13 13:03:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 554, '腐乳', 1, 9.8, 'CNY', 340, 3, 340, 3, 'price', 1, '2026-03-13 13:04:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 562, '耙耙柑', 4, 4.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:03:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 325, '尖椒', 4, 3.88, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:18:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 2, '鸡蛋', 4, 18.8, 'CNY', 30, 18, 30, 18, 'price', 1, '2026-03-15 09:20:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 65, '洋葱', 4, 1.68, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:20:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 28, '蒜', 4, 3.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:21:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 87, '土豆', 4, 1.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:21:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 97, '胡萝卜', 4, 1.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:21:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 79, '皮蛋', 4, 10, 'CNY', 16, 18, 16, 18, 'price', 1, '2026-03-15 09:22:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 78, '黄瓜', 4, 3.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:22:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 1, '西葫芦', 4, 1.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:22:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 481, '苦瓜', 4, 5.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:22:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 129, '花菜', 4, 2.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:23:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 276, '西兰花', 4, 3.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:23:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 119, '番茄', 4, 2.68, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:23:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 145, '包菜', 4, 1.38, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:24:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 30, '娃娃菜', 4, 2.68, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:24:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 320, '大白菜', 4, 1.28, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:24:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 248, '香菇', 4, 8.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:25:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 614, '蒜苔', 4, 5.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:25:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 324, '老豆腐', 4, 4.56, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-15 09:26:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 287, '干豆腐', 4, 13.96, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-15 09:26:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 486, '千张', 4, 11.96, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-15 09:27:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 149, '豆腐', 4, 4.76, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-15 09:27:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 64, '豆芽', 4, 1.18, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:28:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 445, '香蕉', 4, 3.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:29:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 382, '莲藕', 4, 3.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:29:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 103, '大葱', 4, 0.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:29:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 185, '芹菜', 4, 1.18, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:29:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 121, '香葱', 4, 4.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:30:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 161, '蒜苗', 4, 6.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:30:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 63, '青菜', 4, 1.78, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:31:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 282, '鸡爪', 4, 24.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:33:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 516, '鸡翅中', 4, 29.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:33:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 275, '鸡腿', 4, 6.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:34:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 39, '鸡胸肉', 4, 7.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:34:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 585, '手枪腿（或者鸡胸脯肉）', 4, 5.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:34:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 113, '羊排', 4, 29.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:34:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 118, '牛肉', 4, 35.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:35:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 377, '梅头猪肉', 4, 13.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:35:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 74, '五花肉', 4, 12.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:36:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 75, '里脊肉', 4, 15.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 09:36:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 445, '香蕉', 3, 4.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:00:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 325, '尖椒', 3, 4.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:01:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 614, '蒜苔', 3, 4.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:01:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 105, '香菜', 3, 10.35, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:02:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 410, '韭菜', 3, 2.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:02:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 246, '冬笋', 3, 5.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:02:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 136, '豆角', 3, 5.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:03:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 161, '蒜苗', 3, 6.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:03:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 103, '大葱', 3, 1.75, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:03:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 121, '香葱', 3, 7.1, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:03:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 235, '小茴香', 3, 9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:04:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 185, '芹菜', 3, 1.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:04:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 78, '黄瓜', 3, 3.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:04:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 1, '西葫芦', 3, 2.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:04:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 119, '番茄', 3, 2.78, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:04:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 248, '香菇', 3, 8.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:05:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 320, '大白菜', 3, 1.28, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:05:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 129, '花菜', 3, 2.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:05:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 276, '西兰花', 3, 3.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:05:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 30, '娃娃菜', 3, 2.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:06:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 63, '青菜', 3, 1.7, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:06:00.000000');

-- --- 批次 3 (记录 201-300) ---
INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 67, '生菜', 3, 1.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:06:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 575, '菠菜', 3, 2, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:06:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 481, '苦瓜', 3, 4.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:07:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 258, '油麦菜', 3, 3.3, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:07:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 117, '菜心', 3, 6.85, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:07:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 145, '包菜', 3, 0.99, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:08:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 27, '姜', 3, 5.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:08:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 87, '土豆', 3, 2.18, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:08:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 97, '胡萝卜', 3, 1.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:08:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 65, '洋葱', 3, 1.28, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:09:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 28, '蒜', 3, 5.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:09:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 81, '纯牛奶', 3, 7.9, 'CNY', 950, 5, 950, 5, 'price', 1, '2026-03-15 10:10:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 228, '肥牛片', 3, 37.9, 'CNY', 400, 3, 400, 3, 'price', 1, '2026-03-15 10:11:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 350, '前腿肉', 3, 8.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:12:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 75, '里脊肉', 3, 9.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:12:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 74, '五花肉', 3, 9.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:12:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 2, '鸡蛋', 3, 19.9, 'CNY', 30, 18, 30, 18, 'price', 1, '2026-03-15 10:13:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 505, '腊肉', 3, 19.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:14:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 317, '腊肠', 3, 19.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:14:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 295, '小米', 3, 4.99, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:14:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 619, '干燕麦片', 3, 5.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:15:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 142, '大米', 3, 2.18, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:15:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 146, '粉丝', 3, 16.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:16:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 409, '银耳', 3, 79.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:16:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 301, '桂圆干', 3, 19.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:16:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 331, '木耳（干）', 3, 69.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:17:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 56, '冰糖', 3, 5.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:17:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 26, '白砂糖', 3, 3.88, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-15 10:17:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 15, '面粉', 3, 17.9, 'CNY', 5, 2, 5000, 3, 'price', 1, '2026-03-16 03:05:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 562, '耙耙柑', 3, 4.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:06:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 147, '菜籽油', 3, 65, 'CNY', 5, 4, 5000, 5, 'price', 1, '2026-03-16 03:06:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 86, '花生油', 3, 98, 'CNY', 5, 4, 5000, 5, 'price', 1, '2026-03-16 03:07:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 358, '玉米油', 3, 80.9, 'CNY', 6.18, 4, 6180, 5, 'price', 1, '2026-03-16 03:07:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 391, '挂面', 3, 4.9, 'CNY', 800, 3, 800, 3, 'price', 1, '2026-03-16 03:08:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 31, '老抽', 3, 9.9, 'CNY', 1.33, 4, 1330, 5, 'price', 1, '2026-03-16 03:09:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 46, '蚝油', 3, 8.9, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-16 03:09:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 24, '生抽', 3, 10.9, 'CNY', 1.25, 4, 1250, 5, 'price', 1, '2026-03-16 03:09:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 10, '料酒', 3, 8.9, 'CNY', 2, 4, 2000, 5, 'price', 1, '2026-03-16 03:10:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 103, '大葱', 3, 1.65, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:11:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 185, '芹菜', 3, 1.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:11:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 121, '香葱', 3, 7.1, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:12:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 235, '小茴香', 3, 9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:12:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 410, '韭菜', 3, 2.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:12:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 105, '香菜', 3, 8.55, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:13:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 63, '青菜', 3, 1.7, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:13:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 67, '生菜', 3, 1.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:13:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 117, '菜心', 3, 6.85, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:13:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 575, '菠菜', 3, 2, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:13:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 78, '黄瓜', 3, 3.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:14:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 481, '苦瓜', 3, 4.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:14:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 258, '油麦菜', 3, 3.7, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:14:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 214, '茭白', 3, 13.9, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-16 03:15:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 136, '豆角', 3, 5.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:15:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 325, '尖椒', 3, 4.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:15:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 119, '番茄', 3, 2.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:16:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 248, '香菇', 3, 8.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:16:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 320, '大白菜', 3, 1.28, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:17:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 30, '娃娃菜', 3, 2.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:17:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 276, '西兰花', 3, 3.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:17:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 129, '花菜', 3, 2.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:17:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 97, '胡萝卜', 3, 1.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:18:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 65, '洋葱', 3, 1.28, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:18:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 87, '土豆', 3, 2.28, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:18:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 145, '包菜', 3, 0.99, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:19:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 39, '鸡胸肉', 3, 5.99, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:19:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 516, '鸡翅中', 3, 25.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:19:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 275, '鸡腿', 3, 8.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:19:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 199, '鸭肉', 3, 3.99, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:20:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 350, '前腿肉', 3, 6.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:20:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 75, '里脊肉', 3, 15.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:20:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 74, '五花肉', 3, 14.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:21:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 198, '猪蹄', 3, 19.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:21:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 2, '鸡蛋', 3, 19.9, 'CNY', 30, 18, 30, 18, 'price', 1, '2026-03-16 03:21:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 79, '皮蛋', 3, 5, 'CNY', 10, 18, 10, 18, 'price', 1, '2026-03-16 03:22:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 324, '老豆腐', 3, 1.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:22:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 486, '千张', 3, 15.6, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-16 03:23:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 287, '干豆腐', 3, 13.6, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-16 03:23:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 64, '豆芽', 3, 1.28, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:23:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 149, '豆腐', 3, 3.98, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-16 03:23:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 620, '鲜鸭血', 3, 3.9, 'CNY', 400, 3, 400, 3, 'price', 1, '2026-03-16 03:24:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 1, '西葫芦', 3, 2.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 03:25:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 136, '豆角', 1, 6.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:43:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 325, '尖椒', 1, 4.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:44:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 562, '耙耙柑', 1, 4.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:44:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 445, '香蕉', 1, 3.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:44:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 78, '黄瓜', 1, 3.78, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:45:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 481, '苦瓜', 1, 5.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:45:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 30, '娃娃菜', 1, 2.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:45:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 145, '包菜', 1, 1.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:45:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 320, '大白菜', 1, 1.28, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:46:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 129, '花菜', 1, 2.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:46:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 614, '蒜苔', 1, 5.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:46:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 248, '香菇', 1, 8.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:46:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 119, '番茄', 1, 2.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:47:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 87, '土豆', 1, 1.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:47:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 97, '胡萝卜', 1, 1.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:47:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 382, '莲藕', 1, 3.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:48:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 258, '油麦菜', 1, 3.28, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:48:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 277, '空心菜', 1, 3.28, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:48:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 575, '菠菜', 1, 1.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:48:00.000000');

-- --- 批次 4 (记录 301-400) ---
INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 63, '青菜', 1, 1.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:48:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 67, '生菜', 1, 1.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:49:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 410, '韭菜', 1, 2.18, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:49:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 103, '大葱', 1, 1.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:49:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 185, '芹菜', 1, 1.28, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:50:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 232, '香芹', 1, 2.68, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:50:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 161, '蒜苗', 1, 1.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:50:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 121, '香葱', 1, 3.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:50:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 28, '蒜', 1, 3.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:51:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 65, '洋葱', 1, 1.68, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:51:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 64, '豆芽', 1, 1.08, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:52:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 324, '老豆腐', 1, 5.16, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-16 09:52:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 149, '豆腐', 1, 2.38, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:52:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 2, '鸡蛋', 1, 15.8, 'CNY', 30, 18, 30, 18, 'price', 1, '2026-03-16 09:53:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 282, '鸡爪', 1, 19.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:53:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 275, '鸡腿', 1, 6.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:53:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 516, '鸡翅中', 1, 29.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:54:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 585, '手枪腿（或者鸡胸脯肉）', 1, 7.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:54:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 350, '前腿肉', 1, 8.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:54:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 469, '肉馅', 1, 6.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:54:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 74, '五花肉', 1, 15.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:55:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 377, '梅头猪肉', 1, 12.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:55:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 75, '里脊肉', 1, 15.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:55:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 118, '牛肉', 1, 37.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:56:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 295, '小米', 1, 2.99, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:57:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 290, '花生', 1, 6.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:57:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 142, '大米', 1, 2.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:57:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 294, '黑米', 1, 4.5, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-16 09:57:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 147, '菜籽油', 1, 69, 'CNY', 5, 4, 5000, 5, 'price', 1, '2026-03-16 09:58:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 445, '香蕉', 2, 2.99, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:43:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 295, '小米', 2, 4.99, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:44:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 142, '大米', 2, 3.28, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:44:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 294, '黑米', 2, 3.99, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:44:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 26, '白砂糖', 2, 3.99, 'CNY', 1, 7, 500, 3, 'purchase', 1, '2026-03-18 03:44:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 290, '花生', 2, 5.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:45:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 15, '面粉', 2, 1.99, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:45:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 619, '干燕麦片', 2, 4.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:45:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 297, '绿豆', 2, 6.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:46:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 291, '红豆', 2, 9.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:46:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 2, '鸡蛋', 2, 13.9, 'CNY', 30, 18, 30, 18, 'price', 1, '2026-03-18 03:47:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 64, '豆芽', 2, 0.99, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:48:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 448, '巴沙鱼', 2, 8.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:48:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 213, '虾皮', 2, 26.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:48:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 49, '青椒', 2, 4.59, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:48:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 119, '番茄', 2, 2.88, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:49:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 1, '西葫芦', 2, 1.69, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:49:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 78, '黄瓜', 2, 2.99, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:50:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 325, '尖椒', 2, 4.39, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:50:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 145, '包菜', 2, 3.58, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-18 03:50:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 129, '花菜', 2, 2.59, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:50:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 87, '土豆', 2, 1.99, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:51:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 65, '洋葱', 2, 0.59, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:51:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 165, '荔浦芋头', 2, 2.99, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:51:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 185, '芹菜', 2, 0.79, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:51:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 258, '油麦菜', 2, 2.79, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:52:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 410, '韭菜', 2, 2.38, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:52:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 575, '菠菜', 2, 1.18, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:52:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 67, '生菜', 2, 0.79, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:52:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 63, '青菜', 2, 0.69, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:52:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 105, '香菜', 2, 4.69, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:53:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 79, '皮蛋', 2, 0.6, 'CNY', 1, 18, 1, 18, 'price', 1, '2026-03-18 03:53:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 350, '前腿肉', 2, 6.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:53:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 285, '莴笋', 2, 1.29, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:53:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 161, '蒜苗', 2, 1.49, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:54:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 382, '莲藕', 2, 3.59, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:54:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 27, '姜', 2, 5.88, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:54:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 28, '蒜', 2, 6.88, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:54:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 103, '大葱', 2, 1.39, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:55:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 74, '五花肉条', 2, 10.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:55:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 39, '鸡胸肉', 2, 5.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:55:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 275, '鸡腿', 2, 6.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:56:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 486, '千张', 2, 4.99, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:56:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 149, '豆腐', 2, 1.99, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 03:56:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 562, '耙耙柑', 4, 5.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:43:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 248, '香菇', 4, 8.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:43:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 614, '蒜苔', 4, 5.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:43:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 136, '豆角', 4, 5.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:44:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 325, '尖椒', 4, 4.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:44:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 49, '青椒', 4, 4.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:44:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 28, '蒜', 4, 3.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:45:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 129, '花菜', 4, 3.28, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:45:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 276, '西兰花', 4, 3.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:45:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 65, '洋葱', 4, 1.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:45:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 1, '西葫芦', 4, 1.88, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:46:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 481, '苦瓜', 4, 5.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:46:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 78, '黄瓜', 4, 3.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:46:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 119, '番茄', 4, 2.68, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:46:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 145, '包菜', 4, 1.18, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:47:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 30, '娃娃菜', 4, 2.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:47:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 320, '大白菜', 4, 1.28, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:47:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 410, '韭菜', 4, 2.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:47:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 63, '青菜', 4, 2.68, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:47:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 121, '香葱', 4, 4.68, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:48:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 2, '鸡蛋', 4, 18.8, 'CNY', 30, 18, 30, 18, 'price', 1, '2026-03-18 08:48:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 103, '大葱', 4, 0.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:49:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 185, '芹菜', 4, 2.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:49:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 382, '莲藕', 4, 3.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:50:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 282, '鸡爪', 4, 24.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:51:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 516, '鸡翅中', 4, 29.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:51:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 275, '鸡腿', 4, 7.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:51:00.000000');

-- --- 批次 5 (记录 401-475) ---
INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 39, '鸡胸肉', 4, 7.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:52:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 585, '手枪腿（或者鸡胸脯肉）', 4, 8.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:52:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 113, '羊排', 4, 29.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:52:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 102, '羊肉', 4, 39.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:52:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 118, '牛肉', 4, 35.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:53:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 350, '前腿肉', 4, 8.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:53:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 469, '肉馅', 4, 9.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:53:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 75, '里脊肉', 4, 15.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:53:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 74, '五花肉', 4, 12.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:54:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 97, '胡萝卜', 4, 1.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:57:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 87, '土豆', 4, 1.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 08:57:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 177, '啤酒', 4, 6.9, 'CNY', 1, 4, 1000, 5, 'price', 1, '2026-03-18 08:58:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 344, '米酒', 4, 12.9, 'CNY', 750, 5, 750, 5, 'price', 1, '2026-03-18 08:58:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 32, '干辣椒', 4, 37.6, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-18 08:59:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 12, '桂皮', 4, 78, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-18 09:00:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 482, '白胡椒', 4, 113.8, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-18 09:01:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 55, '香叶', 4, 89, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-18 09:01:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 431, '辣椒面', 4, 43.8, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-18 09:01:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 270, '草果', 4, 93.6, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-18 09:02:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 259, '茴香', 4, 25.6, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-18 09:02:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 104, '孜然粉', 4, 99, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-18 09:03:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 85, '黑芝麻', 4, 37.8, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-18 09:03:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 116, '白芝麻', 4, 29.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 09:03:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 11, '八角', 4, 74.8, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-18 09:03:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 426, '陈皮', 4, 68, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-18 09:04:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 292, '红枣', 4, 30.6, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-18 09:04:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 88, '蕨根粉', 4, 13, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 09:04:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 295, '小米', 4, 2.99, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 09:05:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 290, '花生', 4, 6.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 09:06:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 294, '黑米', 4, 4.5, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 09:06:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 298, '黄豆', 4, 7.36, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-18 09:06:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 297, '绿豆', 4, 15.8, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-18 09:06:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 289, '糯米', 4, 7.96, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-18 09:07:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 291, '红豆', 4, 13.96, 'CNY', 1, 2, 1000, 3, 'price', 1, '2026-03-18 09:07:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 391, '挂面', 4, 3.9, 'CNY', 900, 3, 900, 3, 'price', 1, '2026-03-18 09:08:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 15, '面粉', 4, 19.9, 'CNY', 5, 2, 5000, 3, 'price', 1, '2026-03-18 09:08:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 142, '大米', 4, 2.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-18 09:09:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 562, '耙耙柑', 4, 5.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:29:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 248, '香菇', 4, 8.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:30:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 320, '大白菜', 4, 1.38, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:30:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 30, '娃娃菜', 4, 2.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:31:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 67, '生菜', 4, 4.38, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:31:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 145, '包菜', 4, 1.18, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:31:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 185, '芹菜', 4, 2.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:31:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 119, '番茄', 4, 2.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:32:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 97, '胡萝卜', 4, 1.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:32:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 87, '土豆', 4, 1.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:32:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 28, '蒜', 4, 3.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:32:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 65, '洋葱', 4, 1.68, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:33:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 78, '黄瓜', 4, 3.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:33:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 1, '西葫芦', 4, 2.18, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:33:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 481, '苦瓜', 4, 5.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:34:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 129, '花菜', 4, 3.68, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:34:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 276, '西兰花', 4, 3.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:34:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 325, '尖椒', 4, 4.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:34:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 49, '青椒', 4, 4.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:34:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 614, '蒜苔', 4, 5.58, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:35:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 110, '金针菇', 4, 3, 'CNY', 250, 3, 250, 3, 'price', 1, '2026-03-19 06:35:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 410, '韭菜', 4, 2.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:36:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 63, '青菜', 4, 2.68, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:36:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 258, '油麦菜', 4, 3.98, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:36:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 282, '鸡爪', 4, 24.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:37:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 516, '鸡翅中', 4, 29.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:38:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 275, '鸡腿', 4, 6.99, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:38:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 585, '手枪腿（或者鸡胸脯肉）', 4, 8.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:38:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 39, '鸡胸肉', 4, 7.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:38:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 113, '羊排', 4, 29.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:38:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 102, '羊肉', 4, 39.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:39:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 118, '牛肉', 4, 35.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:39:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 198, '猪蹄', 4, 19.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:39:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 350, '前腿肉', 4, 8.8, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:39:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 74, '五花肉', 4, 12.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:40:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 75, '里脊肉', 4, 10.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:40:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 469, '肉馅', 4, 9.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:40:00.000000');

INSERT INTO product_records (user_id, product_id, product_name, merchant_id, price, currency, original_quantity, original_unit_id, standard_quantity, standard_unit_id, record_type, exchange_rate, recorded_at)
VALUES (1, 339, '猪前肘', 4, 8.9, 'CNY', 1, 7, 500, 3, 'price', 1, '2026-03-19 06:41:00.000000');

-- ============================================================
-- 迁移统计
-- ============================================================
-- 用户: 1 条
-- 商家: 4 条
-- 新建原料: 2 个
-- 新建商品: 2 个
-- 价格记录: 475 条
-- 总计 INSERT 语句: 484 条