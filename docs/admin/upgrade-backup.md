# 升级与备份

这篇讲怎么升级生计、怎么备份恢复、出问题怎么排查。

## 升级流程

1. **先备份**（见下）
2. **拉代码**：`git pull`
3. **装新依赖**：
   - 后端：`cd backend && uv sync`（或 `pip install -r requirements.txt`）
   - 前端：`cd frontend && npm install`
4. **表结构迁移**：如果这次升级涉及表结构变更，跑 `backend/scripts/sql/` 下对应引擎的脚本（每个变更提供 SQLite / MySQL / PostgreSQL / PostGIS 四套）
5. **重启服务**：开发模式 `--reload` 会自动重载；生产手动重启 uvicorn
6. **前端重新构建**：生产环境 `npm run build` 后刷新浏览器

> 改了 Python 文件后若"修复似乎没生效"，清一下 `__pycache__` 再重启，避免缓存假阴性。

## 备份

定期备份这三样：

- **数据库**：
  - SQLite：直接拷贝 `backend/data/livecalc.db`（建议先停服务或用 `.backup` 避免写中途拷）
  - MySQL：`mysqldump`
  - PostgreSQL：`pg_dump`
- **配置**：`backend/.env`、`frontend/.env`（含密钥，妥善保管）
- **数据导出**（可选）：用系统的数据导出功能导出 `full` 包（见 [个人中心 · 数据导出](../profile.md#数据导出)）

## 恢复

- 还原数据库文件 / 导入 dump
- 还原 `.env`
- 重启服务

## 日志

- 后端日志写在 `LOG_DIR`（默认 `backend/logs`），`LOG_LEVEL=INFO` 记录请求/异常
- 排查问题时临时调 `LOG_LEVEL=DEBUG` 看详情
- 错误会记录请求 URL、方式、请求体、响应体、异常堆栈（传给前端的仍是人话错误信息，不泄露堆栈）

## 常见排障

| 现象 | 排查 |
|---|---|
| 启动报错 | 看 `logs/`；常见是 `.env` 缺项或数据库连不上 |
| `database is locked`（SQLite） | 写并发冲突。开发可调 `busy_timeout`；生产建议换 MySQL/PG |
| 连接池耗尽（`QueuePool limit reached`） | 长持有连接叠加。查是否有长事务、SSE 流期间白占连接 |
| 价格/趋势时区错位 | 确认前端每个请求都带 `X-Timezone` 头（拦截器）；本系统统一按用户本地日 |
| 改 Python 后假阴性 | 清 `__pycache__` 重启 |
| USDA 下载失败 | USDA WAF 概率切断；系统已用完整 UA + 并发重试兜底，差窗口多重试几次 |
| Agent 任务卡住 | 看 [Agent 任务台](agent.md) 的超时配置（`AGENT_*`） |

## 已知注意点

- **时间口径**：系统里所有"按日"判定以**用户本地日**为准（通过 `X-Timezone` 头）。如果服务器和用户跨时区，趋势横轴的"今天"以用户时区为准。
- **alembic**：项目用 `create_all` 建表，不走 alembic。表结构变更靠 `scripts/sql/` 脚本。
- **软删除**：所有删除都是软删除（`is_active=False`），可恢复。
