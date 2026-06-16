CREATE TABLE IF NOT EXISTS usda_foods (
    id SERIAL PRIMARY KEY,
    fdc_id INTEGER NOT NULL,
    data_type VARCHAR(32) NOT NULL,
    description VARCHAR(512) NOT NULL,
    description_zh VARCHAR(512),
    translate_status VARCHAR(16) NOT NULL DEFAULT 'pending',
    publication_date VARCHAR(32),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    CONSTRAINT uq_usda_foods_fdc_id UNIQUE (fdc_id)
);
CREATE INDEX IF NOT EXISTS ix_usda_foods_fdc_id ON usda_foods (fdc_id);
CREATE INDEX IF NOT EXISTS ix_usda_foods_data_type ON usda_foods (data_type);
CREATE INDEX IF NOT EXISTS ix_usda_foods_description ON usda_foods (description);
CREATE INDEX IF NOT EXISTS ix_usda_foods_description_zh ON usda_foods (description_zh);

CREATE TABLE IF NOT EXISTS usda_food_nutrients (
    id SERIAL PRIMARY KEY,
    fdc_id INTEGER NOT NULL,
    nutrient_no VARCHAR(16),
    name VARCHAR(255) NOT NULL,
    name_zh VARCHAR(255),
    amount DOUBLE PRECISION NOT NULL,
    unit_name VARCHAR(32) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_usda_food_nutrients_fdc_id ON usda_food_nutrients (fdc_id);

CREATE TABLE IF NOT EXISTS translation_configs (
    id SERIAL PRIMARY KEY,
    config JSONB NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS usda_tasks (
    id SERIAL PRIMARY KEY,
    task_type VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'pending',
    progress JSONB,
    provider VARCHAR(32),
    error_log TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_usda_tasks_task_type ON usda_tasks (task_type);
