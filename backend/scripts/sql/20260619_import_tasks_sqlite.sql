-- SQLite: 创建 import_tasks 表

CREATE TABLE import_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'pending',
    progress JSON,
    stats JSON,
    error TEXT,
    user_id INTEGER REFERENCES users(id),
    created_at DATETIME,
    updated_at DATETIME
);
CREATE INDEX ix_import_tasks_id ON import_tasks (id);
CREATE INDEX ix_import_tasks_task_type ON import_tasks (task_type);
