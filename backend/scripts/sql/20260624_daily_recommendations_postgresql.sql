-- 每日饮食推荐 + 用户营养目标
-- 引擎：PostgreSQL（未启用 PostGIS）

-- users 表新增字段
ALTER TABLE users ADD COLUMN daily_calorie_target DOUBLE PRECISION DEFAULT 2000;
ALTER TABLE users ADD COLUMN daily_protein_target DOUBLE PRECISION DEFAULT 60;
ALTER TABLE users ADD COLUMN daily_carb_target DOUBLE PRECISION DEFAULT 300;
ALTER TABLE users ADD COLUMN daily_fat_target DOUBLE PRECISION DEFAULT 65;
ALTER TABLE users ADD COLUMN daily_budget DOUBLE PRECISION DEFAULT NULL;

-- 创建 daily_recommendations 表
CREATE TABLE IF NOT EXISTS daily_recommendations (
    id SERIAL NOT NULL,
    user_id INTEGER NOT NULL,
    date DATE NOT NULL,
    meal_type VARCHAR(20) NOT NULL,
    recipe_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (user_id, date, meal_type),
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (recipe_id) REFERENCES recipes (id)
);

CREATE INDEX IF NOT EXISTS ix_daily_recommendations_id ON daily_recommendations (id);
