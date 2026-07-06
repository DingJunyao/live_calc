-- 商品价格权重 + 用户覆盖表（SQLite）
-- 适用于：SQLite（含开发库 backend/data/livecalc.db 直接补）

-- 1. products 加权重列（SQLite 3.37+ 支持 inline CHECK；ADD COLUMN 带 CHECK 需 3.31+）
ALTER TABLE products ADD COLUMN price_weight INTEGER NOT NULL DEFAULT 50
  CHECK (price_weight BETWEEN 0 AND 100);

-- 2. 用户覆盖表
CREATE TABLE IF NOT EXISTS user_product_weight_overrides (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  product_id INTEGER NOT NULL REFERENCES products(id),
  weight INTEGER NOT NULL DEFAULT 50 CHECK (weight BETWEEN 0 AND 100),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME,
  created_by INTEGER,
  updated_by INTEGER,
  is_active INTEGER DEFAULT 1,   -- SQLite 无原生 BOOL，按项目惯例 1/0
  UNIQUE(user_id, product_id)
);
CREATE INDEX IF NOT EXISTS ix_upwo_user_active ON user_product_weight_overrides(user_id, is_active);
CREATE INDEX IF NOT EXISTS ix_user_product_weight_overrides_product_id ON user_product_weight_overrides(product_id);
