-- 每日饮食推荐 + 用户营养目标
-- 引擎：MySQL

-- users 表新增字段
ALTER TABLE users ADD COLUMN daily_calorie_target FLOAT DEFAULT 2000;
ALTER TABLE users ADD COLUMN daily_protein_target FLOAT DEFAULT 60;
ALTER TABLE users ADD COLUMN daily_carb_target FLOAT DEFAULT 300;
ALTER TABLE users ADD COLUMN daily_fat_target FLOAT DEFAULT 65;
ALTER TABLE users ADD COLUMN daily_budget FLOAT NULL DEFAULT NULL;

-- 创建 daily_recommendations 表
CREATE TABLE IF NOT EXISTS daily_recommendations (
    id INTEGER NOT NULL AUTO_INCREMENT,
    user_id INTEGER NOT NULL,
    date DATE NOT NULL,
    meal_type VARCHAR(20) NOT NULL,
    recipe_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_user_date_meal (user_id, date, meal_type),
    INDEX ix_daily_recommendations_id (id),
    CONSTRAINT fk_daily_rec_user FOREIGN KEY (user_id) REFERENCES users (id),
    CONSTRAINT fk_daily_rec_recipe FOREIGN KEY (recipe_id) REFERENCES recipes (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
