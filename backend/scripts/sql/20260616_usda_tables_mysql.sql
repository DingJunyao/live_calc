CREATE TABLE IF NOT EXISTS usda_foods (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fdc_id INT NOT NULL,
    data_type VARCHAR(32) NOT NULL,
    description VARCHAR(512) NOT NULL,
    description_zh VARCHAR(512) NULL,
    translate_status VARCHAR(16) NOT NULL DEFAULT 'pending',
    publication_date VARCHAR(32) NULL,
    created_at DATETIME NULL,
    updated_at DATETIME NULL,
    UNIQUE KEY uq_usda_foods_fdc_id (fdc_id),
    KEY ix_usda_foods_fdc_id (fdc_id),
    KEY ix_usda_foods_data_type (data_type),
    KEY ix_usda_foods_description (description),
    KEY ix_usda_foods_description_zh (description_zh)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS usda_food_nutrients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fdc_id INT NOT NULL,
    nutrient_no VARCHAR(16) NULL,
    name VARCHAR(255) NOT NULL,
    name_zh VARCHAR(255) NULL,
    amount FLOAT NOT NULL,
    unit_name VARCHAR(32) NOT NULL,
    KEY ix_usda_food_nutrients_fdc_id (fdc_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS translation_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config JSON NOT NULL,
    created_at DATETIME NULL,
    updated_at DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS usda_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_type VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'pending',
    progress JSON NULL,
    provider VARCHAR(32) NULL,
    error_log TEXT NULL,
    created_at DATETIME NULL,
    updated_at DATETIME NULL,
    KEY ix_usda_tasks_task_type (task_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
