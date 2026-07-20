-- 行政区划表 + User region_id（PostgreSQL，无 PostGIS）
-- 执行前备份数据库！

CREATE TABLE IF NOT EXISTS administrative_regions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(12) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    parent_id INT REFERENCES administrative_regions(id),
    level INT NOT NULL,
    iso_country VARCHAR(2),
    path VARCHAR(200),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_administrative_regions_parent_id ON administrative_regions(parent_id);
CREATE INDEX IF NOT EXISTS ix_administrative_regions_level ON administrative_regions(level);

ALTER TABLE users ADD COLUMN region_id INT REFERENCES administrative_regions(id);

-- 验证
-- \d administrative_regions
-- \d users
