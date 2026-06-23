-- 快速填写自定义商品顺序 - 用户 × 商家 × 商品每日排序记录

CREATE TABLE IF NOT EXISTS user_merchant_product_orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    merchant_id INTEGER NOT NULL REFERENCES merchants(id),
    product_id  INTEGER NOT NULL REFERENCES products(id),
    session_date DATE NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  DATETIME DEFAULT (datetime('now')),
    UNIQUE(user_id, merchant_id, product_id, session_date)
);

CREATE INDEX IF NOT EXISTS idx_umpo_lookup
    ON user_merchant_product_orders(user_id, merchant_id, session_date);
