CREATE TABLE IF NOT EXISTS usda_foods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fdc_id INTEGER NOT NULL UNIQUE,
    data_type TEXT NOT NULL,
    description TEXT NOT NULL,
    description_zh TEXT,
    translate_status TEXT NOT NULL DEFAULT 'pending',
    publication_date TEXT,
    created_at DATETIME,
    updated_at DATETIME
);
CREATE INDEX IF NOT EXISTS ix_usda_foods_fdc_id ON usda_foods (fdc_id);
CREATE INDEX IF NOT EXISTS ix_usda_foods_data_type ON usda_foods (data_type);
CREATE INDEX IF NOT EXISTS ix_usda_foods_description ON usda_foods (description);
CREATE INDEX IF NOT EXISTS ix_usda_foods_description_zh ON usda_foods (description_zh);

CREATE TABLE IF NOT EXISTS usda_food_nutrients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fdc_id INTEGER NOT NULL,
    nutrient_no TEXT,
    name TEXT NOT NULL,
    name_zh TEXT,
    amount REAL NOT NULL,
    unit_name TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_usda_food_nutrients_fdc_id ON usda_food_nutrients (fdc_id);

CREATE TABLE IF NOT EXISTS translation_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config TEXT NOT NULL,
    created_at DATETIME,
    updated_at DATETIME
);

CREATE TABLE IF NOT EXISTS usda_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    progress TEXT,
    provider TEXT,
    error_log TEXT,
    created_at DATETIME,
    updated_at DATETIME
);
CREATE INDEX IF NOT EXISTS ix_usda_tasks_task_type ON usda_tasks (task_type);
