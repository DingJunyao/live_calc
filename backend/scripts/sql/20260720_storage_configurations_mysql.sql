-- 图片存储配置表（单行，DB 字段非空则覆盖 .env BOOTSTRAP_*）
-- 引擎：MySQL

CREATE TABLE IF NOT EXISTS storage_configurations (
    id INTEGER NOT NULL AUTO_INCREMENT,
    backend VARCHAR(10) NOT NULL DEFAULT 'local',
    storage_base_url VARCHAR(255),
    s3_endpoint VARCHAR(255),
    s3_access_key VARCHAR(255),
    s3_secret_key VARCHAR(255),
    s3_bucket VARCHAR(255),
    s3_region VARCHAR(64),
    s3_url_style VARCHAR(10) NOT NULL DEFAULT 'path',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL,
    PRIMARY KEY (id)
);
