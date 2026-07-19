-- 给 map_configurations 表新增 map_enabled 总开关字段（默认 true）
-- SQLite：直接 ADD COLUMN（Boolean 即 integer 别名，server_default true 由 SQLite 3.23+ 解析为 1）
ALTER TABLE map_configurations ADD COLUMN map_enabled BOOLEAN NOT NULL DEFAULT 1;
