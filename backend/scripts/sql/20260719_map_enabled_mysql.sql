-- 给 map_configurations 表新增 map_enabled 总开关字段（默认 true）
-- MySQL：BOOLEAN 即 TINYINT(1)，true 解析为 1
ALTER TABLE map_configurations
    ADD COLUMN map_enabled BOOLEAN NOT NULL DEFAULT TRUE;
