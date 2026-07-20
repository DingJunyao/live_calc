-- 行政区划表 + User region_id（MySQL）
-- 执行前备份数据库！

CREATE TABLE IF NOT EXISTS administrative_regions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(12) NOT NULL,
    name VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    parent_id INT,
    level INT NOT NULL,
    iso_country VARCHAR(2),
    path VARCHAR(200),
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_administrative_regions_code (code),
    FOREIGN KEY (parent_id) REFERENCES administrative_regions(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_administrative_regions_level ON administrative_regions(level);

ALTER TABLE users ADD COLUMN region_id INT;
ALTER TABLE users ADD FOREIGN KEY (region_id) REFERENCES administrative_regions(id);

-- 验证
-- DESCRIBE administrative_regions;
-- DESCRIBE users;
