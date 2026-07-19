-- 给 map_configurations 表新增 map_enabled 总开关字段（默认 true）
-- PostgreSQL：严格 boolean 类型，server_default 必须是 true/false
ALTER TABLE map_configurations
    ADD COLUMN map_enabled BOOLEAN NOT NULL DEFAULT TRUE;
