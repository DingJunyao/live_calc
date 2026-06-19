-- Agent 维护任务台：3 张表
-- 引擎：MySQL
-- 与 alembic 迁移 20260619_1129_c63850795dc5 保持一致

-- agent_sessions：Agent 会话记录
CREATE TABLE agent_sessions (
    id INTEGER NOT NULL AUTO_INCREMENT,
    task_type VARCHAR(32) NULL,
    title VARCHAR(128) NULL,
    status VARCHAR(20) NOT NULL,
    runner_type VARCHAR(20) NOT NULL,
    claude_session_id VARCHAR(128) NULL,
    initial_prompt TEXT NULL,
    cost_usd DECIMAL(10, 4) NULL,
    error TEXT NULL,
    user_id INTEGER NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_agent_sessions_task_type (task_type),
    KEY ix_agent_sessions_id (id),
    CONSTRAINT fk_agent_sessions_user FOREIGN KEY (user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- agent_messages：Agent 会话消息
CREATE TABLE agent_messages (
    id INTEGER NOT NULL AUTO_INCREMENT,
    session_id INTEGER NULL,
    seq INTEGER NULL,
    role VARCHAR(16) NULL,
    content TEXT NULL,
    tool_name VARCHAR(64) NULL,
    tool_use_id VARCHAR(64) NULL,
    tool_input JSON NULL,
    tool_result JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_agent_messages_session_id (session_id),
    KEY ix_agent_messages_id (id),
    KEY ix_agent_messages_tool_use_id (tool_use_id),
    CONSTRAINT fk_agent_messages_session FOREIGN KEY (session_id) REFERENCES agent_sessions (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- agent_approvals：Agent 危险 SQL 审批
CREATE TABLE agent_approvals (
    id INTEGER NOT NULL AUTO_INCREMENT,
    session_id INTEGER NULL,
    message_id INTEGER NULL,
    sql TEXT NOT NULL,
    danger_reason VARCHAR(128) NULL,
    affected_estimate INTEGER NULL,
    status VARCHAR(20) NOT NULL,
    decided_by INTEGER NULL,
    decided_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_agent_approvals_session_id (session_id),
    KEY ix_agent_approvals_id (id),
    CONSTRAINT fk_agent_approvals_session FOREIGN KEY (session_id) REFERENCES agent_sessions (id),
    CONSTRAINT fk_agent_approvals_message FOREIGN KEY (message_id) REFERENCES agent_messages (id),
    CONSTRAINT fk_agent_approvals_decided_by FOREIGN KEY (decided_by) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 注：entity_unit_overrides.source 字段取值说明（注释级变更，无 DDL）
-- 取值：import（导入自动创建）/ manual（手动维护）/ agent（Agent 维护任务写入）
