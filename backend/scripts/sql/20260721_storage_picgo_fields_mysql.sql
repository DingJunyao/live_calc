-- 图片存储配置表加 PicGo 三字段（S3 专用）
-- 引擎：MySQL

ALTER TABLE storage_configurations ADD COLUMN s3_base_path VARCHAR(255) NULL;
ALTER TABLE storage_configurations ADD COLUMN s3_custom_domain VARCHAR(255) NULL;
ALTER TABLE storage_configurations ADD COLUMN s3_url_suffix VARCHAR(255) NULL;
