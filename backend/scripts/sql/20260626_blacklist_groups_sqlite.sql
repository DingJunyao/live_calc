-- 原料黑名单分组相关表（SQLite）
-- 适用于离线开发环境
-- 注：本脚本为最终结构（含表/列重命名后的形态），供全新初始化使用

CREATE TABLE IF NOT EXISTS blacklist_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS blacklist_group_ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL REFERENCES blacklist_groups(id),
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
    is_ai_matched INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id),
    UNIQUE(group_id, ingredient_id)
);

CREATE TABLE IF NOT EXISTS blacklist_group_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    blacklist_group_id INTEGER NOT NULL REFERENCES blacklist_groups(id),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id),
    UNIQUE(user_id, blacklist_group_id)
);

CREATE TABLE IF NOT EXISTS user_ingredient_blacklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
    reason TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    blacklist_group_id INTEGER REFERENCES blacklist_groups(id),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id),
    UNIQUE(user_id, ingredient_id)
);

CREATE INDEX IF NOT EXISTS idx_blacklist_user ON user_ingredient_blacklist(user_id);
CREATE INDEX IF NOT EXISTS idx_blacklist_ingredient ON user_ingredient_blacklist(ingredient_id);
CREATE INDEX IF NOT EXISTS idx_blacklist_group ON user_ingredient_blacklist(blacklist_group_id);
CREATE INDEX IF NOT EXISTS idx_bgi_group ON blacklist_group_ingredients(group_id);
CREATE INDEX IF NOT EXISTS idx_bgi_ingredient ON blacklist_group_ingredients(ingredient_id);
CREATE INDEX IF NOT EXISTS idx_bgs_user ON blacklist_group_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_bgs_group ON blacklist_group_subscriptions(blacklist_group_id);
