-- 原料黑名单分组相关表（PostgreSQL，无 PostGIS）
-- 注：本脚本为最终结构（含表/列重命名后的形态），供全新初始化使用

CREATE TABLE IF NOT EXISTS blacklist_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_order INT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by INT REFERENCES users(id),
    updated_by INT REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS blacklist_group_ingredients (
    id SERIAL PRIMARY KEY,
    group_id INT NOT NULL REFERENCES blacklist_groups(id),
    ingredient_id INT NOT NULL REFERENCES ingredients(id),
    is_ai_matched BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by INT REFERENCES users(id),
    updated_by INT REFERENCES users(id),
    UNIQUE(group_id, ingredient_id)
);

CREATE TABLE IF NOT EXISTS blacklist_group_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id),
    blacklist_group_id INT NOT NULL REFERENCES blacklist_groups(id),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by INT REFERENCES users(id),
    updated_by INT REFERENCES users(id),
    UNIQUE(user_id, blacklist_group_id)
);

CREATE TABLE IF NOT EXISTS user_ingredient_blacklist (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id),
    ingredient_id INT NOT NULL REFERENCES ingredients(id),
    reason VARCHAR(100),
    source VARCHAR(50) NOT NULL DEFAULT 'manual',
    blacklist_group_id INT REFERENCES blacklist_groups(id),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by INT REFERENCES users(id),
    updated_by INT REFERENCES users(id),
    UNIQUE(user_id, ingredient_id)
);

CREATE INDEX IF NOT EXISTS idx_blacklist_user ON user_ingredient_blacklist(user_id);
CREATE INDEX IF NOT EXISTS idx_blacklist_ingredient ON user_ingredient_blacklist(ingredient_id);
CREATE INDEX IF NOT EXISTS idx_blacklist_group ON user_ingredient_blacklist(blacklist_group_id);
CREATE INDEX IF NOT EXISTS idx_bgi_group ON blacklist_group_ingredients(group_id);
CREATE INDEX IF NOT EXISTS idx_bgi_ingredient ON blacklist_group_ingredients(ingredient_id);
CREATE INDEX IF NOT EXISTS idx_bgs_user ON blacklist_group_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_bgs_group ON blacklist_group_subscriptions(blacklist_group_id);
