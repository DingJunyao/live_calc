-- 商品价格权重 + 用户覆盖表（MySQL 8.0+）
ALTER TABLE products
  ADD COLUMN price_weight INT NOT NULL DEFAULT 50,
  ADD CONSTRAINT ck_products_price_weight_range CHECK (price_weight BETWEEN 0 AND 100);

CREATE TABLE IF NOT EXISTS user_product_weight_overrides (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  product_id INT NOT NULL,
  weight INT NOT NULL DEFAULT 50,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  created_by INT,
  updated_by INT,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  CONSTRAINT ck_upwo_weight_range CHECK (weight BETWEEN 0 AND 100),
  CONSTRAINT uq_user_product_weight UNIQUE (user_id, product_id),
  CONSTRAINT fk_upwo_user FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_upwo_product FOREIGN KEY (product_id) REFERENCES products(id),
  KEY ix_upwo_user_active (user_id, is_active),
  KEY ix_user_product_weight_overrides_product_id (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
