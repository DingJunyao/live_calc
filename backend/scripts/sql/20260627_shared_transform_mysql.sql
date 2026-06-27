-- 共享转型 schema 变更（MySQL）
-- 1) merchants.user_id 改 nullable（语义从「拥有者」改为「录入者」）
-- 2) recipes.is_public 新增（区分私有/公开菜谱）
-- 3) units.is_standard 新增（标准单位标记；unit_system 已存在）
-- 4) user_merchant_favorites 收藏表（替代原 user_id 私有归属语义）
-- 5) product_merchant_price_summary 价格聚合汇总表（去标识）

-- 1) merchants.user_id 改 nullable（MODIFY COLUMN 是幂等的）
ALTER TABLE merchants MODIFY COLUMN user_id INT NULL;

-- 2) recipes.is_public（IF NOT EXISTS 仅 MySQL 8.0.29+ 支持；用存储过程兼容旧版）
-- 此处假设 MySQL 8.0+，若列已存在会报错，请注释跳过。
ALTER TABLE recipes ADD COLUMN is_public TINYINT(1) NOT NULL DEFAULT 0;

-- 3) units.is_standard
ALTER TABLE units ADD COLUMN is_standard TINYINT(1) NOT NULL DEFAULT 0;

-- 4) 收藏表
CREATE TABLE IF NOT EXISTS user_merchant_favorites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    merchant_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_user_merchant (user_id, merchant_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (merchant_id) REFERENCES merchants(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_user_merchant_favorites_user_id ON user_merchant_favorites(user_id);
CREATE INDEX ix_user_merchant_favorites_merchant_id ON user_merchant_favorites(merchant_id);

-- 5) 价格聚合汇总表
CREATE TABLE IF NOT EXISTS product_merchant_price_summary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    merchant_id INT,
    sample_count INT NOT NULL DEFAULT 0,
    recent_price DECIMAL(10, 2),
    avg_price_30d DECIMAL(10, 2),
    min_price DECIMAL(10, 2),
    max_price DECIMAL(10, 2),
    last_updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (merchant_id) REFERENCES merchants(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_pmp_summary_product ON product_merchant_price_summary(product_id);
CREATE INDEX ix_pmp_summary_merchant ON product_merchant_price_summary(merchant_id);

-- 收藏回填：现有「拥有」商家 → 收藏
INSERT IGNORE INTO user_merchant_favorites (user_id, merchant_id, created_at)
SELECT DISTINCT user_id, id, NOW() FROM merchants WHERE user_id IS NOT NULL;
