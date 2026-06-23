CREATE TABLE IF NOT EXISTS user_merchant_product_orders (
    id          INT PRIMARY KEY AUTO_INCREMENT,
    user_id     INT NOT NULL,
    merchant_id INT NOT NULL,
    product_id  INT NOT NULL,
    session_date DATE NOT NULL,
    sort_order  INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_umpo_user_merchant_product_date (user_id, merchant_id, product_id, session_date),
    INDEX idx_umpo_lookup (user_id, merchant_id, session_date),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (merchant_id) REFERENCES merchants(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
