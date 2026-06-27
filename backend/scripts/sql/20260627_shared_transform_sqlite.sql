-- 共享转型 schema 变更（SQLite）
-- 1) merchants.user_id 改 nullable（语义从「拥有者」改为「录入者」）
-- 2) recipes.is_public 新增（区分私有/公开菜谱）
-- 3) units.is_standard 新增（标准单位标记；unit_system 已存在）
-- 4) user_merchant_favorites 收藏表（替代原 user_id 私有归属语义）
-- 5) product_merchant_price_summary 价格聚合汇总表（去标识）
--
-- 注意：SQLite 对 ALTER 的支持有限——
--   - merchants.user_id 由 NOT NULL 改 nullable 必须走表重建（alembic batch_alter_table 已处理）；
--   - recipes.is_public / units.is_standard 用 ADD COLUMN，但 SQLite 无 IF NOT EXISTS 语义，
--     重复执行会报错，故此处注释保留语句，由 alembic 迁移或一次性手动执行。
-- 新建库应在 merchants/recipes/units 建表 DDL 中直接包含对应列定义。

-- 2) recipes.is_public（一次性执行；已存在请跳过）
-- ALTER TABLE recipes ADD COLUMN is_public BOOLEAN NOT NULL DEFAULT 0;

-- 3) units.is_standard（一次性执行；已存在请跳过）
-- ALTER TABLE units ADD COLUMN is_standard BOOLEAN NOT NULL DEFAULT 0;

-- 4) 收藏表
CREATE TABLE IF NOT EXISTS user_merchant_favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    merchant_id INTEGER NOT NULL REFERENCES merchants(id),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, merchant_id)
);
CREATE INDEX IF NOT EXISTS ix_user_merchant_favorites_user_id ON user_merchant_favorites(user_id);
CREATE INDEX IF NOT EXISTS ix_user_merchant_favorites_merchant_id ON user_merchant_favorites(merchant_id);

-- 5) 价格聚合汇总表
CREATE TABLE IF NOT EXISTS product_merchant_price_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id),
    merchant_id INTEGER REFERENCES merchants(id),
    sample_count INTEGER NOT NULL DEFAULT 0,
    recent_price NUMERIC(10, 2),
    avg_price_30d NUMERIC(10, 2),
    min_price NUMERIC(10, 2),
    max_price NUMERIC(10, 2),
    last_updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_pmp_summary_product ON product_merchant_price_summary(product_id);
CREATE INDEX IF NOT EXISTS ix_pmp_summary_merchant ON product_merchant_price_summary(merchant_id);

-- 收藏回填：现有「拥有」商家 → 收藏
INSERT OR IGNORE INTO user_merchant_favorites (user_id, merchant_id, created_at)
SELECT DISTINCT user_id, id, CURRENT_TIMESTAMP FROM merchants WHERE user_id IS NOT NULL;
