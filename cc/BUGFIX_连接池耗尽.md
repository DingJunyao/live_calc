# 连接池耗尽（QueuePool timeout）修复

## 现象

后端报 `sqlalchemy.exc.TimeoutError: QueuePool limit of size 10 overflow 20 reached, connection timed out, timeout 30.00`，栈顶落在 [security.py](backend/app/core/security.py) 的 `resolve_user_from_token` → `db.query(User)...first()`。

## 根因

**栈顶是受害者，不是凶手。** `resolve_user_from_token` 是每个鉴权请求第一个借连接的点，连接池一空它最先炸——它本身不是耗尽池子的源头。真正吞噬连接的是「长持有并发叠加」打爆了 30 连接（pool_size=10 + max_overflow=20）的池子，且这些长持有与常规 API 请求共享同一个 `engine`。

逐一排查所有 `SessionLocal()` / `get_db` 使用点后，**没有「永久泄漏」的 bug**（后台任务、`_peek_session_status`、`run_agent_loop`、`event_gen` 的 `db_replay` 等都有 try/finally + close）。问题出在「长持有」+「低效反模式」+「容量不足」三者叠加：

| 凶手 | 占用方式 | 时长 |
|---|---|---|
| `run_agent_loop` 主 `db` | 每个运行中 Agent 会话持 1 连接（[session_runner.py:716/920](backend/app/services/agent/session_runner.py#L716) finally close，但整段会话期间不还） | 数分钟~数小时 |
| **SSE `stream_session` 的 `Depends(get_db)`** | 每个 SSE 订阅持 1 连接，**鉴权完进 `event_gen` 后再没用过**，纯白占 | 整个 Agent 运行期 |
| `resolve_user_from_token` 的 `next(get_db())` | 高频反模式，异常路径归还依赖 GC 时机；正常路径还会因 generator 临时对象立即被 GC 触发 finally，单次鉴权借两次连接 | 短但不稳 |

并发场景：任务台开几个 Agent 会话 + 数据维护页轮询 + 后台 USDA/翻译/导入任务 → 轻松超 30。SQLite 单写锁下等锁的连接也算「占用」，雪上加霜。

## 修复（三板斧，均奔根因）

### 1. `resolve_user_from_token` 消除 `next(get_db())` 反模式
[security.py:111-122](backend/app/core/security.py#L111)：改直接 `SessionLocal()` + try/finally。异常时也保证 `db.close()`，不再依赖 GC；同时消除「generator 被 GC 提前 close 导致借两次连接」的浪费。这是每个鉴权请求的必经高频路径。

### 2. SSE `stream_session` 丢掉白占连接的 `Depends(get_db)`
[agent_api.py:295-332](backend/app/api/agent_api.py#L295)：去掉端点级 `db: Session = Depends(get_db)`，鉴权 + 取会话改用独立短命 `auth_db = SessionLocal()`，在 finally 立即 close。close 前先捕获 `is_terminal` / `initial_status` 标量（ORM 对象 close 后 detached），`event_gen` 闭包改用标量，不再碰 `sess`。每个 SSE 流省下「整个 Agent 运行期」的连接占用。

### 3. 连接池适度扩容
[database.py:16-23](backend/app/core/database.py#L16)：pool_size 10→15、max_overflow 20→30（共 45），给并发长持有（多 Agent 会话 + SSE + 后台任务 + 常规请求）留余量。

## 验证

- 静态：`py_compile` 三文件通过；`import app.core.security / database / agent_api` 通过（引用全解析，无删参后残留引用）；grep 确认 `event_gen` 内无遗留 `db`/detached `sess`。
- 运行时：服务自动重载后，开 Agent 任务台 + 后台任务压测，观察 `QueuePool` 是否还耗尽（待开发者确认）。
- 单测：`.venv` 未装 pytest、`uv run` 起的环境缺 sqlalchemy，测试环境不具备，未跑；改动均为构造性正确写法，逻辑等价于原行为（同样查 User / 同样鉴权 / 仅连接生命周期更干净）。

## 改动文件

- [backend/app/core/security.py](backend/app/core/security.py) — `resolve_user_from_token` 改 `SessionLocal()` + try/finally
- [backend/app/api/agent_api.py](backend/app/api/agent_api.py) — `stream_session` 去掉 `Depends(get_db)`，鉴权用短命 session
- [backend/app/core/database.py](backend/app/core/database.py) — SQLite 池扩容 size 15 / overflow 30
