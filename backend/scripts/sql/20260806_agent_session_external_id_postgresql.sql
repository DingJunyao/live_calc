-- =====================================================================
-- agent_sessions.claude_session_id 改名为 external_session_id
-- 引擎：PostgreSQL
-- 日期：2026-08-06
--
-- 说明：
--   * PostgreSQL 的 RENAME COLUMN 会保留原列数据。
--   * 该列没有索引/外键，直接改名即可。
--   * 执行前请先备份。
-- =====================================================================

ALTER TABLE agent_sessions
  RENAME COLUMN claude_session_id TO external_session_id;

-- 降级：
-- ALTER TABLE agent_sessions
--   RENAME COLUMN external_session_id TO claude_session_id;
