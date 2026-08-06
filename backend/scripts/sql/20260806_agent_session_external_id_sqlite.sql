-- =====================================================================
-- agent_sessions.claude_session_id 改名为 external_session_id
-- 引擎：SQLite
-- 日期：2026-08-06
--
-- 说明：
--   * SQLite 对 DROP COLUMN 的兼容性取决于版本，这里沿用仓库已有
--     「建新表 → 复制 → 删旧表 → 改名 → 重建索引」流程。
--   * 执行前请先备份：.backup livecalc.db livecalc.db.bak 或直接复制文件。
-- =====================================================================

BEGIN TRANSACTION;

-- 1. 建新表，字段名使用 external_session_id
CREATE TABLE agent_sessions_new (
	id INTEGER NOT NULL,
	task_type VARCHAR(32),
	title VARCHAR(128),
	status VARCHAR(20) NOT NULL,
	runner_type VARCHAR(20) NOT NULL,
	external_session_id VARCHAR(128),
	initial_prompt TEXT,
	cost_usd NUMERIC(10, 4),
	error TEXT,
	user_id INTEGER,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
);

-- 2. 复制旧数据
INSERT INTO agent_sessions_new (
	id, task_type, title, status, runner_type,
	external_session_id, initial_prompt, cost_usd, error, user_id,
	created_at, updated_at
)
SELECT
	id, task_type, title, status, runner_type,
	claude_session_id, initial_prompt, cost_usd, error, user_id,
	created_at, updated_at
FROM agent_sessions;

-- 3. 替换旧表
DROP TABLE agent_sessions;
ALTER TABLE agent_sessions_new RENAME TO agent_sessions;

-- 4. 重建索引
CREATE INDEX ix_agent_sessions_id ON agent_sessions (id);
CREATE INDEX ix_agent_sessions_task_type ON agent_sessions (task_type);

COMMIT;
