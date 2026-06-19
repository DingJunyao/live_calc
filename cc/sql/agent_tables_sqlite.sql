-- Agent 维护任务台：3 张表
-- 引擎：SQLite
-- 与 alembic 迁移 20260619_1129_c63850795dc5 保持一致

-- agent_sessions：Agent 会话记录
CREATE TABLE agent_sessions (
    id INTEGER NOT NULL,
    task_type VARCHAR(32),
    title VARCHAR(128),
    status VARCHAR(20) NOT NULL,
    runner_type VARCHAR(20) NOT NULL,
    claude_session_id VARCHAR(128),
    initial_prompt TEXT,
    cost_usd NUMERIC(10, 4),
    error TEXT,
    user_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    PRIMARY KEY (id)
);
CREATE INDEX ix_agent_sessions_id ON agent_sessions (id);
CREATE INDEX ix_agent_sessions_task_type ON agent_sessions (task_type);

-- agent_messages：Agent 会话消息
CREATE TABLE agent_messages (
    id INTEGER NOT NULL,
    session_id INTEGER,
    seq INTEGER,
    role VARCHAR(16),
    content TEXT,
    tool_name VARCHAR(64),
    tool_use_id VARCHAR(64),
    tool_input JSON,
    tool_result JSON,
    created_at DATETIME DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (session_id) REFERENCES agent_sessions (id),
    PRIMARY KEY (id)
);
CREATE INDEX ix_agent_messages_id ON agent_messages (id);
CREATE INDEX ix_agent_messages_session_id ON agent_messages (session_id);
CREATE INDEX ix_agent_messages_tool_use_id ON agent_messages (tool_use_id);

-- agent_approvals：Agent 危险 SQL 审批
CREATE TABLE agent_approvals (
    id INTEGER NOT NULL,
    session_id INTEGER,
    message_id INTEGER,
    sql TEXT NOT NULL,
    danger_reason VARCHAR(128),
    affected_estimate INTEGER,
    status VARCHAR(20) NOT NULL,
    decided_by INTEGER,
    decided_at DATETIME,
    created_at DATETIME DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (decided_by) REFERENCES users (id),
    FOREIGN KEY (message_id) REFERENCES agent_messages (id),
    FOREIGN KEY (session_id) REFERENCES agent_sessions (id),
    PRIMARY KEY (id)
);
CREATE INDEX ix_agent_approvals_id ON agent_approvals (id);
CREATE INDEX ix_agent_approvals_session_id ON agent_approvals (session_id);

-- 注：entity_unit_overrides.source 字段取值说明（注释级变更，无 DDL）
-- 取值：import（导入自动创建）/ manual（手动维护）/ agent（Agent 维护任务写入）
