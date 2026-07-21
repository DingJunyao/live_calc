-- 图片存储配置表加 PicGo 三字段（S3 专用）
-- 引擎：SQLite

ALTER TABLE storage_configurations ADD COLUMN s3_base_path TEXT;
ALTER TABLE storage_configurations ADD COLUMN s3_custom_domain TEXT;
ALTER TABLE storage_configurations ADD COLUMN s3_url_suffix TEXT;
