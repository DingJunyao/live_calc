"""runner_factory - 构造 ClaudeCodeRunner + 生成 mcp_config.json（Task 5）。

职责：
1. 生成临时 mcp_config.json，指向 controlled_db_mcp.py（stdio 子进程），
   通过 env 字段注入 ``LIVECALC_DB_URL``。
2. 构造 ``ClaudeCodeRunner``：allowed_tools 对齐 controlled_db_mcp 暴露的
   ``db_read`` / ``describe`` / ``list_tables``，cwd=backend，max_budget_usd
   透传。

设计要点：
- mcp_config 的 server 名固定 ``controlled_db``，工具名前缀 ``mcp__controlled_db__``。
- db_url 通过 env 传递（比 argv 稳，避免路径含空格/转义）。
- SQLite 相对路径（``sqlite:///./data/livecalc.db``）需相对 backend 目录解析成
  绝对路径，否则 MCP 子进程的 cwd 可能不同导致读错文件。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from app.services.agent.claude_code_runner import ClaudeCodeRunner

__all__ = [
    "make_mcp_config_path",
    "build_runner",
    "resolve_db_url",
    "allowed_tools_for_db",
    "MCP_SERVER_NAME",
    "DB_URL_ENV_VAR",
]

# MCP server 名（与工具名前缀对齐：``mcp__controlled_db__db_read``）。
MCP_SERVER_NAME = "controlled_db"

# controlled_db_mcp 通过此 env 读 db_url（见 controlled_db_mcp._resolve_db_url）。
DB_URL_ENV_VAR = "LIVECALC_DB_URL"

# 默认放 backend/data/agent_mcp_config.json（与项目数据目录对齐）。
_DEFAULT_CONFIG_DIRNAME = "data"
_DEFAULT_CONFIG_FILENAME = "agent_mcp_config.json"


def _backend_root() -> Path:
    """返回 backend 目录绝对路径（本模块位于 backend/app/services/agent/）。"""
    return Path(__file__).resolve().parents[3]


def _root_venv_python() -> str:
    """返回可执行 MCP 子进程的 python 绝对路径。

    优先 ``sys.executable``（后端进程自身的解释器，必然能 import 项目依赖包——
    最稳）；否则回退到项目根 ``.venv/Scripts/python.exe``（Windows）或
    ``.venv/bin/python``（Linux/macOS）。

    早期实现曾硬编码 ``D:/code/live_calc/.venv``，跨机器/部署不可靠，已废弃：
    只在 ``sys.executable`` 不可用时（理论上不会发生）作为兜底路径。
    """
    if sys.executable:
        return sys.executable
    # Windows 布局兜底。
    candidate = _backend_root().parent / ".venv" / "Scripts" / "python.exe"
    if candidate.exists():
        return str(candidate)
    # Linux/macOS 布局兜底。
    candidate2 = _backend_root().parent / ".venv" / "bin" / "python"
    if candidate2.exists():
        return str(candidate2)
    # 极端兜底（不应到达）。
    return "python"


def resolve_db_url(raw_url: str | None = None) -> str:
    """把 settings.DATABASE_URL（可能含相对 SQLite 路径）解析成绝对连接串。

    - 非 SQLite 原样返回。
    - SQLite 相对路径（``sqlite:///./data/...`` / ``sqlite:///data/...``）
      按 backend 目录解析成绝对路径，避免 MCP 子进程 cwd 不同时读错文件。
    """
    if raw_url is None:
        from app.config import settings

        raw_url = settings.database_url

    if not raw_url.startswith("sqlite"):
        return raw_url

    prefix = "sqlite:///"
    path_part = raw_url[len(prefix):]
    # 已是绝对路径或纯内存库（``sqlite://``）原样返回。
    if path_part.startswith("/") or path_part == "" or ":memory:" in path_part:
        return raw_url
    # 去掉前导 ``./`` 后按 backend 目录解析。
    rel = path_part.lstrip("./") if path_part.startswith("./") else path_part
    abs_path = (_backend_root() / rel).resolve()
    return f"{prefix}{abs_path.as_posix()}"


def allowed_tools_for_db() -> list[str]:
    """controlled_db MCP 暴露的只读工具白名单。"""
    return [
        f"mcp__{MCP_SERVER_NAME}__db_read",
        f"mcp__{MCP_SERVER_NAME}__describe",
        f"mcp__{MCP_SERVER_NAME}__list_tables",
    ]


def make_mcp_config_path(db_url: str, *, config_path: str | os.PathLike[str] | None = None) -> str:
    """生成 mcp_config.json，指向 controlled_db_mcp.py（stdio 子进程）。

    db_url 通过 env 字段注入（``LIVECALC_DB_URL``），避免 argv 路径含空格问题。

    Args:
        db_url: 已解析的绝对 db_url（用 ``resolve_db_url`` 处理过）。
        config_path: 自定义输出路径；None 时放 backend/data/agent_mcp_config.json。

    Returns:
        mcp_config.json 的绝对路径字符串。
    """
    backend = _backend_root()
    if config_path is None:
        config_dir = backend / _DEFAULT_CONFIG_DIRNAME
        config_dir.mkdir(parents=True, exist_ok=True)
        out_path = config_dir / _DEFAULT_CONFIG_FILENAME
    else:
        out_path = Path(config_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "mcpServers": {
            MCP_SERVER_NAME: {
                "type": "stdio",
                "command": _root_venv_python(),
                "args": ["-m", "app.services.agent.controlled_db_mcp"],
                "cwd": str(backend),
                "env": {DB_URL_ENV_VAR: db_url},
            }
        }
    }
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return str(out_path)


def build_runner(
    task_type: str,
    db_url: str,
    *,
    max_budget_usd: "float | None" = None,
    idle_timeout: "float | None" = None,
    total_timeout: "float | None" = None,
    extra_env: "dict[str, str] | None" = None,
    cli: "str | None" = None,
    mcp_config_path: "str | None" = None,
) -> ClaudeCodeRunner:
    """构造 ``ClaudeCodeRunner``，对接 controlled_db MCP。

    Args:
        task_type: 任务类型（保留入参，目前未影响 Runner 行为；Task 6 接模板）。
        db_url: 原始 db_url（内部用 ``resolve_db_url`` 解析）。
        max_budget_usd: 成本上限，透传 ``--max-budget-usd``。
        idle_timeout / total_timeout: CLI 子进程超时（秒），None 用 Runner 默认。
        extra_env: 追加到子进程 env。
        cli: CLI 可执行文件名/路径覆盖。
        mcp_config_path: 自定义 mcp_config 路径，None 时自动生成。

    Returns:
        配置好的 ``ClaudeCodeRunner`` 实例。
    """
    del task_type  # 当前不影响 Runner 构造；Task 6 接模板时再处理 prompt。

    resolved_url = resolve_db_url(db_url)
    config_path = mcp_config_path or make_mcp_config_path(resolved_url)
    cwd = str(_backend_root())

    kwargs: dict[str, Any] = {
        "mcp_config_path": config_path,
        "allowed_tools": allowed_tools_for_db(),
        "cwd": cwd,
        "max_budget_usd": max_budget_usd,
        "extra_env": extra_env,
        "cli": cli,
    }
    if idle_timeout is not None:
        kwargs["idle_timeout"] = idle_timeout
    if total_timeout is not None:
        kwargs["total_timeout"] = total_timeout

    return ClaudeCodeRunner(**kwargs)
