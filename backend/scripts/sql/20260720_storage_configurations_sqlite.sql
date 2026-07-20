-- 图片存储配置表（单行，DB 字段非空则覆盖 .env BOOTSTRAP_*）
-- 引擎：SQLite

CREATE TABLE IF NOT EXISTS storage_configurations (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    backend TEXT NOT NULL DEFAULT 'local',
    storage_base_url TEXT,
    s3_endpoint TEXT,
    s3_access_key TEXT,
    s3_secret_key TEXT,
    s3_bucket TEXT,
    s3_region TEXT,
    s3_url_style TEXT NOT NULL DEFAULT 'path',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

CREATE INDEX ix_storage_configurations_id ON storage_configurations (id);
