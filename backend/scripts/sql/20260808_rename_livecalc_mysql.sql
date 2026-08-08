-- ============================================================
-- 项目名称统一：live_calc → livecalc（数据库残留清理）
-- 引擎：MySQL
-- 日期：2026-08-08
-- 说明：以下表中残留了旧项目名 live_calc 的历史记录（非配置数据），
--       均为 Agent 会话历史和错误日志，改不改都不影响功能。
--       执行前建议备份数据库。
-- ============================================================

-- 备份提示：
--   mysqldump -u root -p livecalc > livecalc_backup_20260808.sql

-- 1. agent_messages — 工具调用/返回中的 MCP server 名和文件路径
UPDATE agent_messages
SET tool_input = REPLACE(tool_input, 'live_calc', 'livecalc')
WHERE tool_input LIKE '%live_calc%';

UPDATE agent_messages
SET tool_result = REPLACE(tool_result, 'live_calc', 'livecalc')
WHERE tool_result LIKE '%live_calc%';

-- 2. usda_tasks — 错误日志中的文件路径
UPDATE usda_tasks
SET error_log = REPLACE(error_log, 'live_calc', 'livecalc')
WHERE error_log LIKE '%live_calc%';

-- 验证
SELECT 'agent_messages.tool_input' AS table_name, COUNT(*) AS cnt FROM agent_messages WHERE tool_input LIKE '%live_calc%'
UNION ALL
SELECT 'agent_messages.tool_result', COUNT(*) FROM agent_messages WHERE tool_result LIKE '%live_calc%'
UNION ALL
SELECT 'usda_tasks.error_log', COUNT(*) FROM usda_tasks WHERE error_log LIKE '%live_calc%';
-- 预期：全部为 0
