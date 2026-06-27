-- 共享转型 schema 变更（PostgreSQL，无 PostGIS；本变更与地理列无关）
-- 1) merchants.user_id 改 nullable（语义从「拥有者」改为「录入者」）
-- 2) recipes.is_public 新增（区分私有/公开菜谱）
-- 3) units.is_standard 新增（标准单位标记；unit_system 已存在）
-- 4) user_merchant_favorites 收藏表（替代原 user_id 私有归属语义）
-- 5) product_merchant_price_summary 价格聚合汇总表（去标识）

-- 1) merchants.user_id 改 nullable
ALTER TABLE merchants ALTER COLUMN user_id DROP NOT NULL;

-- 2) recipes.is_public（ADD COLUMN IF NOT EXISTS 幂等）
ALTER TABLE recipes ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT FALSE;

-- 3) units.is_standard
ALTER TABLE units ADD COLUMN IF NOT EXISTS is_standard BOOLEAN NOT NULL DEFAULT FALSE;

-- 4) 收藏表
CREATE TABLE IF NOT EXISTS user_merchant_favorites (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id),
    merchant_id INT NOT NULL REFERENCES merchants(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_merchant UNIQUE (user_id, merchant_id)
);
CREATE INDEX IF NOT EXISTS ix_user_merchant_favorites_user_id ON user_merchant_favorites(user_id);
CREATE INDEX IF NOT EXISTS ix_user_merchant_favorites_merchant_id ON user_merchant_favorites(merchant_id);

-- 5) 价格聚合汇总表
CREATE TABLE IF NOT EXISTS product_merchant_price_summary (
    id SERIAL PRIMARY KEY,
    product_id INT NOT NULL REFERENCES products(id),
    merchant_id INT REFERENCES merchants(id),
    sample_count INT NOT NULL DEFAULT 0,
    recent_price NUMERIC(10, 2),
    avg_price_30d NUMERIC(10, 2),
    min_price NUMERIC(10, 2),
    max_price NUMERIC(10, 2),
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_pmp_summary_product ON product_merchant_price_summary(product_id);
CREATE INDEX IF NOT EXISTS ix_pmp_summary_merchant ON product_merchant_price_summary(merchant_id);

-- 收藏回填：现有「拥有」商家 → 收藏
INSERT INTO user_merchant_favorites (user_id, merchant_id, created_at)
SELECT DISTINCT user_id, id, NOW() FROM merchants WHERE user_id IS NOT NULL
ON CONFLICT (user_id, merchant_id) DO NOTHING;
