-- 原料黑名单与过敏原分组表（PostgreSQL，无 PostGIS）
-- 适用于 PostgreSQL 生产环境

CREATE TABLE IF NOT EXISTS allergen_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_order INT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by INT REFERENCES users(id),
    updated_by INT REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS allergen_group_ingredients (
    id SERIAL PRIMARY KEY,
    group_id INT NOT NULL REFERENCES allergen_groups(id),
    ingredient_id INT NOT NULL REFERENCES ingredients(id),
    is_ai_matched BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by INT REFERENCES users(id),
    updated_by INT REFERENCES users(id),
    UNIQUE(group_id, ingredient_id)
);

CREATE TABLE IF NOT EXISTS user_ingredient_blacklist (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id),
    ingredient_id INT NOT NULL REFERENCES ingredients(id),
    reason VARCHAR(100),
    source VARCHAR(50) NOT NULL DEFAULT 'manual',
    allergen_group_id INT REFERENCES allergen_groups(id),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by INT REFERENCES users(id),
    updated_by INT REFERENCES users(id),
    UNIQUE(user_id, ingredient_id)
);

CREATE INDEX IF NOT EXISTS idx_blacklist_user ON user_ingredient_blacklist(user_id);
CREATE INDEX IF NOT EXISTS idx_blacklist_ingredient ON user_ingredient_blacklist(ingredient_id);
CREATE INDEX IF NOT EXISTS idx_blacklist_allergen_group ON user_ingredient_blacklist(allergen_group_id);
CREATE INDEX IF NOT EXISTS idx_agi_group ON allergen_group_ingredients(group_id);
CREATE INDEX IF NOT EXISTS idx_agi_ingredient ON allergen_group_ingredients(ingredient_id);
