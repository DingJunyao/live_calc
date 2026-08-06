-- =====================================================================
-- agent_sessions.claude_session_id 改名为 external_session_id
-- 引擎：MySQL
-- 日期：2026-08-06
--
-- 说明：
--   * MySQL 使用 CHANGE COLUMN 同时完成改名和类型声明。
--   * 该列没有索引/外键，直接改名即可。
--   * 执行前请先备份。
-- =====================================================================

ALTER TABLE agent_sessions
  CHANGE COLUMN claude_session_id external_session_id VARCHAR(128) NULL;

-- 降级：
-- ALTER TABLE agent_sessions
--   CHANGE COLUMN external_session_id claude_session_id VARCHAR(128) NULL;
