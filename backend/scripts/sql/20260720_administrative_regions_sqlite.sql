-- 行政区划表 + User region_id（SQLite）
-- 适用于离线开发环境
-- 执行前备份 livecalc.db！

CREATE TABLE IF NOT EXISTS administrative_regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(12) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    parent_id INTEGER REFERENCES administrative_regions(id),
    level INTEGER NOT NULL,
    iso_country VARCHAR(2),
    path VARCHAR(200),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS ix_administrative_regions_parent_id ON administrative_regions(parent_id);
CREATE INDEX IF NOT EXISTS ix_administrative_regions_level ON administrative_regions(level);

ALTER TABLE users ADD COLUMN region_id INTEGER REFERENCES administrative_regions(id);

-- 验证
-- PRAGMA table_info(administrative_regions);
-- PRAGMA table_info(users);
