-- 原料黑名单与过敏原分组表（SQLite）
-- 适用于离线开发环境

CREATE TABLE IF NOT EXISTS allergen_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS allergen_group_ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL REFERENCES allergen_groups(id),
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
    is_ai_matched INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id),
    UNIQUE(group_id, ingredient_id)
);

CREATE TABLE IF NOT EXISTS user_ingredient_blacklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
    reason TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    allergen_group_id INTEGER REFERENCES allergen_groups(id),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id),
    UNIQUE(user_id, ingredient_id)
);

CREATE INDEX IF NOT EXISTS idx_blacklist_user ON user_ingredient_blacklist(user_id);
CREATE INDEX IF NOT EXISTS idx_blacklist_ingredient ON user_ingredient_blacklist(ingredient_id);
CREATE INDEX IF NOT EXISTS idx_agi_group ON allergen_group_ingredients(group_id);
CREATE INDEX IF NOT EXISTS idx_agi_ingredient ON allergen_group_ingredients(ingredient_id);
