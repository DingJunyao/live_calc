-- 商品价格权重 + 用户覆盖表（PostgreSQL）
-- 注：本脚本同时适用于「启用 PostGIS 的 PostgreSQL」，本变更与 PostGIS 无关。

ALTER TABLE products
  ADD COLUMN price_weight INTEGER NOT NULL DEFAULT 50,
  ADD CONSTRAINT ck_products_price_weight_range CHECK (price_weight BETWEEN 0 AND 100);

CREATE TABLE IF NOT EXISTS user_product_weight_overrides (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  product_id INTEGER NOT NULL REFERENCES products(id),
  weight INTEGER NOT NULL DEFAULT 50,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ,
  created_by INTEGER,
  updated_by INTEGER,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT ck_upwo_weight_range CHECK (weight BETWEEN 0 AND 100),
  CONSTRAINT uq_user_product_weight UNIQUE (user_id, product_id)
);
CREATE INDEX IF NOT EXISTS ix_upwo_user_active ON user_product_weight_overrides(user_id, is_active);
CREATE INDEX IF NOT EXISTS ix_user_product_weight_overrides_product_id ON user_product_weight_overrides(product_id);
