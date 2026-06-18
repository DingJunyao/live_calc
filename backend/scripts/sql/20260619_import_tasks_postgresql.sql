-- PostgreSQL: 创建 import_tasks 表

CREATE TABLE import_tasks (
    id SERIAL PRIMARY KEY,
    task_type VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'pending',
    progress JSONB,
    stats JSONB,
    error TEXT,
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_import_tasks_task_type ON import_tasks (task_type);
