"""claude_code_runner - 用 subprocess 驱动 claude code CLI 的 stream-json。

设计要点（与 spike ``backend/spikes/agent_cli_probe.py`` 实测一致）：

1. **CLI 嵌套启动陷阱**：后端若跑在 Claude Code 会话内，``CLAUDECODE`` 环境变量会
   让 CLI 拒绝启动（"cannot be launched inside another Claude Code session"），
   ``_build_env`` 必须 pop 掉它。
2. **跨平台线程桥接**：用 ``subprocess.Popen`` + 后台线程逐行读 stdout，通过
   ``queue.Queue`` 把行交给主流程（Windows SelectorEventLoop 不支持 asyncio 子进程）。
3. **必加 CLI flag**：``--output-format stream-json --include-partial-messages
   --verbose --strict-mcp-config``（strict 阻止合并用户全局 MCP，越权风险），
   外加 ``--mcp-config <受控只读 MCP>`` 与 ``--allowedTools <白名单>``；可选
   ``--resume`` / ``--max-budget-usd``。
4. **事件结构**：stream-json 每行一个 JSON。真实增量在 ``stream_event`` 内层
   （content_block_delta.delta.text）。``assistant.message.content`` 数组含
   text / tool_use 块。``user.message.content`` 含 tool_result 块，其 ``content``
   可能是 ``[{type:text,text}]`` 列表、裸字符串、或 JSON 字符串。
   ``result`` 事件携带 is_error / total_cost_usd / permission_denials。
5. 第三方代理 env：继承当前进程 env（已含 ``ANTHROPIC_BASE_URL`` /
   ``ANTHROPIC_AUTH_TOKEN``），仅 pop CLAUDECODE 并强制 UTF-8。

``_build_cmd`` / ``_build_env`` / ``_translate`` 均抽成纯函数便于单测，
``run`` 仅做线程编排。
"""

from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Iterator

from app.services.agent.runner import AgentEvent

__all__ = [
    "ClaudeCodeRunner",
    "build_cmd",
    "build_env",
    "translate_event",
    "describe_exit_code",
]

# --------------------------------------------------------------------------- #
# Windows 退出码 → 人类可读描述
# --------------------------------------------------------------------------- #
# 参考：NTSTATUS values / Win32 error codes
_WIN32_EXIT_CODES: dict[int, str] = {
    0xC0000005: "STATUS_ACCESS_VIOLATION（内存访问违规）",
    0xC0000094: "STATUS_INTEGER_DIVIDE_BY_ZERO（整数除零）",
    0xC00000FD: "STATUS_STACK_OVERFLOW（栈溢出）",
    0xC0000135: "STATUS_DLL_NOT_FOUND（DLL 未找到）",
    0xC0000139: "STATUS_ENTRYPOINT_NOT_FOUND（入口点未找到）",
    0xC0000142: "STATUS_DLL_INIT_FAILED（DLL 初始化失败）",
    0xC0000374: "STATUS_HEAP_CORRUPTION（堆损坏）",
    0xC0000409: "STATUS_STACK_BUFFER_OVERRUN（栈缓冲区溢出）",
    0xC0000417: "STATUS_INVALID_CRUNTIME_PARAMETER（C 运行时参数无效）",
    0xC0000006: "STATUS_IN_PAGE_ERROR（页面调入错误）",
    0xC000001D: "STATUS_ILLEGAL_INSTRUCTION（非法指令）",
    0xC0000022: "STATUS_ACCESS_DENIED（拒绝访问）",
    0xC000008C: "STATUS_ARRAY_BOUNDS_EXCEEDED（数组越界）",
    0xC000008D: "STATUS_FLOAT_DENORMAL_OPERAND（浮点非规格化操作数）",
    0xC000008E: "STATUS_FLOAT_DIVIDE_BY_ZERO（浮点除零）",
    0xC000008F: "STATUS_FLOAT_INEXACT_RESULT（浮点不精确结果）",
    0xC0000090: "STATUS_FLOAT_INVALID_OPERATION（浮点无效操作）",
    0xC0000091: "STATUS_FLOAT_OVERFLOW（浮点溢出）",
    0xC0000092: "STATUS_FLOAT_STACK_CHECK（浮点栈检查）",
    0xC0000093: "STATUS_FLOAT_UNDERFLOW（浮点下溢）",
    0xC0000095: "STATUS_INTEGER_OVERFLOW（整数溢出）",
    0xC0000096: "STATUS_PRIVILEGED_INSTRUCTION（特权指令）",
    0xC00000C5: "STATUS_KERNEL_APC（内核 APC 待处理）",
}

# 通用崩溃码前缀（NTSTATUS error severity）
_STATUS_ERROR_MASK = 0xC0000000

# 0xE0000000 区域的 Node.js / V8 崩溃码
_NODE_CRASH_PREFIXES = (0xE0000000, 0x80000000)


def describe_exit_code(rc: int) -> str:
    """把子进程退出码翻译成人类可读描述（含 Windows NTSTATUS 映射）。

    Args:
        rc: ``Popen.wait()`` 返回的原始退出码（Windows 下为无符号 int）。

    Returns:
        描述字符串，如 ``3225781226 (0xC04583EA) — CLI 自身崩溃（非标准异常码）``。
    """
    base = f"{rc} (0x{rc:08X})"
    # 0) 零/负值：正常或 signal。
    if rc == 0:
        return f"{base} — 正常退出"
    if rc < 0:
        return f"{base} — 进程被信号终止（signal {abs(rc)}）"
    # 1) 已知 NTSTATUS 码（精确匹配，优先级最高）。
    if rc in _WIN32_EXIT_CODES:
        return f"{base} — {_WIN32_EXIT_CODES[rc]}（CLI 自身崩溃）"
    # 2) Node.js / V8 崩溃码区域（0xE... / 0x8...）—— 先于泛 NTSTATUS，避免误判。
    if any((rc & 0xF0000000) == prefix for prefix in _NODE_CRASH_PREFIXES):
        return f"{base} — Node.js / V8 级别崩溃（CLI 自身崩溃）"
    # 3) 泛 NTSTATUS 严重错误（高 2 位为 0xC）。
    if (rc & _STATUS_ERROR_MASK) == _STATUS_ERROR_MASK:
        return f"{base} — NTSTATUS 严重错误（CLI 自身崩溃）"
    # 4) 已知应用层退出码。
    if rc == 1:
        return f"{base} — 一般错误退出"
    return f"{base} — 未知应用退出码（CLI 自身崩溃或逻辑退出）"

# stream_event 内层 delta 中我们关心的文本增量类型。
_TEXT_DELTA = "text_delta"

# CLI 可执行文件名（允许通过环境变量 ``CLAUDE_CLI`` 覆盖）。
_DEFAULT_CLI = "claude"


def build_cmd(
    *,
    prompt: str,
    mcp_config_path: str | os.PathLike[str] | None = None,
    allowed_tools: list[str] | None = None,
    cli: str | None = None,
    resume_session_id: str | None = None,
    max_budget_usd: float | None = None,
    cwd: str | os.PathLike[str] = ".",
) -> list[str]:
    """构造 claude CLI 命令行（纯函数，便于单测）。

    Args:
        prompt: 用户指令文本，作为 ``-p`` 参数透传。
        mcp_config_path: 受控只读 MCP 配置文件路径。
            ``None`` 时不添加 ``--mcp-config``（非 MCP 模式）。
        allowed_tools: 工具白名单，逗号拼接进 ``--allowedTools``。
            ``None`` 时不添加（Agent 可使用默认工具集，含 bash）。
        cli: CLI 可执行文件名/路径，None 时取 ``$CLAUDE_CLI`` 或 ``claude``。
        resume_session_id: 非 None 时附加 ``--resume``。
        max_budget_usd: 非 None 时附加 ``--max-budget-usd``（成本兜底）。
        cwd: 仅用于把相对 ``mcp_config_path`` 解析成绝对路径（与 CLI cwd 对齐）；
            若已是绝对路径则原样使用。

    Returns:
        list[str]: 命令行参数列表。
    """
    cli_resolved = cli or os.environ.get("CLAUDE_CLI") or _DEFAULT_CLI

    cmd: list[str] = [
        cli_resolved,
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--include-partial-messages",
        "--verbose",
    ]

    if mcp_config_path is not None:
        mcp_path = str(Path(mcp_config_path))
        if not os.path.isabs(mcp_path):
            mcp_path = str((Path(cwd) / mcp_path).resolve())
        cmd += ["--strict-mcp-config", "--mcp-config", mcp_path]
        if allowed_tools:
            cmd += ["--allowedTools", ",".join(allowed_tools)]
    else:
        # 非 MCP 模式：明确允许 bash（用于 db_query 查库）+ 基本文件工具
        cmd += ["--allowedTools", "Bash,Read,Write,Edit"]

    if resume_session_id:
        cmd += ["--resume", str(resume_session_id)]
    if max_budget_usd is not None:
        cmd += ["--max-budget-usd", str(max_budget_usd)]
    return cmd


def build_env(extra_env: dict[str, str] | None = None) -> dict[str, str]:
    """构造子进程 env（纯函数，便于单测）。

    - 继承当前进程 env（含 ``ANTHROPIC_BASE_URL`` / ``ANTHROPIC_AUTH_TOKEN``）。
    - **必须 pop ``CLAUDECODE``**，避免 CLI 检测到嵌套启动而拒绝。
    - 强制 ``PYTHONIOENCODING=utf-8``。
    - 应用调用方提供的 ``extra_env``（最后覆盖）。
    """
    env = dict(os.environ)
    env.pop("CLAUDECODE", None)
    env["PYTHONIOENCODING"] = "utf-8"
    if extra_env:
        env.update({k: str(v) for k, v in extra_env.items()})
    return env


def _coerce_tool_result_content(content: Any) -> Any:
    """把 tool_result 的 content 规整成纯文本（两种形态都处理）。

    spike 实测 ``content`` 可能是：
    - 列表 ``[{"type":"text","text":"..."}]``（Anthropic 标准）
    - 裸字符串 ``"{...}"``（部分 MCP / 旧 CLI 版本）
    - 其它（dict 等）：保守用 json.dumps 兜底成字符串。

    返回字符串形式，便于上游统一展示/落库。
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for blk in content:
            if isinstance(blk, dict):
                if blk.get("type") == "text":
                    parts.append(str(blk.get("text", "")))
                else:
                    # 非文本块（image 等）：序列化保留信息。
                    parts.append(json.dumps(blk, ensure_ascii=False))
            else:
                parts.append(str(blk))
        return "".join(parts)
    if isinstance(content, dict):
        # 单 dict（非标准但见过）：原样序列化。
        return json.dumps(content, ensure_ascii=False)
    return str(content)


def translate_event(evt: dict) -> list[AgentEvent]:
    """把一条 stream-json 顶层事件翻译成 0..n 条 ``AgentEvent``（纯函数）。

    映射规则（对照 spike ``events_first.jsonl`` / ``events_resume.jsonl``）：

    - ``system.init`` → 不产事件，但 ``session_id`` 由调用方从 evt 顶层捕获。
      （``session_id`` 在大多数事件的顶层都有，本函数不直接改 Runner 状态，
      只在必要时产一条 session 标记事件——目前不需要，session_id 由 Runner
      在主循环统一从顶层 ``evt.get("session_id")`` 捕获。）
    - ``stream_event.content_block_delta`` 且 ``delta.type == text_delta``
      → 一条 ``text_delta``。**这是唯一的文本源**。
    - ``assistant`` → 遍历 ``message.content``，**只**对每个 tool_use 块产一条
      ``tool_use``。text 块的内容已被 stream_event 的 text_delta 完整覆盖
      （CLI ``--include-partial-messages`` 让两者都发，且实测 stream 聚合文本
      == assistant text 块聚合文本，若都产会重复 2 倍）。
    - ``user`` → 遍历 ``message.content``，每个 tool_result 块产一条 ``tool_result``。
    - ``result`` → 一条 ``done``，带 ``is_error`` / ``cost_usd`` /
      ``permission_denials``；``subtype == "error"`` 时 also 标 ``is_error=True``。
    - 其它事件（message_start / content_block_start / hook_* 等）→ 空列表（忽略）。
    """
    t = evt.get("type")
    out: list[AgentEvent] = []

    if t == "stream_event":
        inner = evt.get("event") or {}
        if inner.get("type") == "content_block_delta":
            delta = inner.get("delta") or {}
            if delta.get("type") == _TEXT_DELTA:
                txt = delta.get("text", "")
                if txt:
                    out.append(AgentEvent(kind="text_delta", text=txt))
        return out

    if t == "assistant":
        msg = evt.get("message") or {}
        for blk in msg.get("content", []) or []:
            if not isinstance(blk, dict):
                continue
            bt = blk.get("type")
            # text 块跳过：其内容已被 stream_event 的 text_delta 完整覆盖，
            # 两者同时产出会导致前端文本重复 2 倍（见模块 docstring）。
            if bt == "tool_use":
                out.append(
                    AgentEvent(
                        kind="tool_use",
                        tool_name=str(blk.get("name", "")),
                        tool_input=blk.get("input") or {},
                        tool_use_id=str(blk.get("id", "")),
                    )
                )
        return out

    if t == "user":
        msg = evt.get("message") or {}
        for blk in msg.get("content", []) or []:
            if not isinstance(blk, dict):
                continue
            if blk.get("type") == "tool_result":
                out.append(
                    AgentEvent(
                        kind="tool_result",
                        tool_use_id=str(blk.get("tool_use_id", "")),
                        tool_result=_coerce_tool_result_content(blk.get("content")),
                    )
                )
        return out

    if t == "result":
        is_error = bool(evt.get("is_error")) or evt.get("subtype") == "error"
        cost = evt.get("total_cost_usd")
        cost_f = float(cost) if isinstance(cost, (int, float)) else None
        denials = evt.get("permission_denials") or []
        out.append(
            AgentEvent(
                kind="done",
                is_error=is_error,
                cost_usd=cost_f,
                permission_denials=list(denials) if isinstance(denials, list) else [],
                error=str(evt.get("subtype") or "") if is_error else "",
            )
        )
        return out

    return out


class ClaudeCodeRunner:
    """用 subprocess 驱动 claude code CLI 的 AgentRunner 实现。

    Example:
        >>> runner = ClaudeCodeRunner(
        ...     mcp_config_path="spikes/mcp_config.json",
        ...     allowed_tools=["mcp__fake_db__db_read"],
        ...     cwd="backend",
        ... )
        >>> for ev in runner.run("查一下有哪些单位"):  # doctest: +SKIP
        ...     print(ev.kind, ev.text[:30])
    """

    def __init__(
        self,
        *,
        mcp_config_path: str | os.PathLike[str] | None = None,
        allowed_tools: list[str] | None = None,
        cwd: str | os.PathLike[str] = ".",
        idle_timeout: float = 120.0,
        total_timeout: float = 600.0,
        max_budget_usd: float | None = None,
        extra_env: dict[str, str] | None = None,
        cli: str | None = None,
    ) -> None:
        """构造 Runner。

        Args:
            mcp_config_path: 受控只读 MCP 配置文件路径。
                ``None`` 时不使用 MCP（Agent 通过 bash + db_query 查库）。
            allowed_tools: 工具白名单。``None`` 时不限制（非 MCP 模式默认行为）。
            cwd: 子进程工作目录。
            idle_timeout: **两行输出之间的最大间隔秒数**（默认 120s）。用于
                ``queue.get`` / stderr drain 超时。超时表示「CLI 卡死、长时间
                无输出」。**不是**任务总超时——长任务里某次工具调用本身耗时
                较长不应误杀，但 120s 完全无任何 token 输出可视为 CLI 卡死。
            total_timeout: **整个任务的墙钟上限秒数**（默认 600s）。在 ``run``
                主循环中用 ``time.monotonic()`` 累计检查，每次取到新行后检查
                ``now - start > total_timeout`` 即产 error 终止。
            max_budget_usd: 透传 ``--max-budget-usd``。
            extra_env: 追加到子进程 env（最终覆盖）。
            cli: CLI 可执行文件名/路径，None 时取 ``$CLAUDE_CLI`` 或 ``claude``。
        """
        self.mcp_config_path = mcp_config_path
        self.allowed_tools = list(allowed_tools) if allowed_tools else None
        self.cwd = str(cwd)
        self.idle_timeout = float(idle_timeout)
        self.total_timeout = float(total_timeout)
        self.max_budget_usd = max_budget_usd
        self.extra_env = dict(extra_env) if extra_env else None
        self.cli = cli

        self._last_session_id: str | None = None
        self._proc: subprocess.Popen[str] | None = None

    # ------------------------------------------------------------------ #
    # AgentRunner 协议
    # ------------------------------------------------------------------ #
    # resume 锚取 last_session_id（CLI 捕获的 claude session id），
    # 非 AgentSession DB PK。与 LangChainRunner.uses_db_pk_resume=True 对称。
    uses_db_pk_resume = False

    @property
    def last_session_id(self) -> str | None:
        return self._last_session_id

    def run(
        self, prompt: str, *, resume_session_id: str | None = None
    ) -> Iterator[AgentEvent]:
        """启动 claude CLI 子进程，流式产出 AgentEvent。

        Yields:
            AgentEvent: 按 stream 顺序；末尾必为 ``done``（CLI 正常终态）或
            ``error``（子进程异常 / 超时）。
        """
        # B-5：强制每次 run 重新捕获 session_id。若上一轮 CLI 未发 system.init
        # （如 --resume 失败），保留旧值会让下一轮 resume 用错 session。
        self._last_session_id = None

        cmd = build_cmd(
            prompt=prompt,
            mcp_config_path=self.mcp_config_path,
            allowed_tools=self.allowed_tools,
            cli=self.cli,
            resume_session_id=resume_session_id,
            max_budget_usd=self.max_budget_usd,
            cwd=self.cwd,
        )
        env = build_env(self.extra_env)

        cli_path = shutil.which(cmd[0]) or cmd[0]
        # 用解析出的绝对路径替换 cmd[0]，避免 Windows CreateProcess 再度搜索 PATH
        # （PATH 搜索在某些场景下会触发 FileNotFoundError，即使文件确实存在）。
        cmd[0] = cli_path
        self._proc = None
        start_time = time.monotonic()
        try:
            self._proc = subprocess.Popen(
                cmd,
                cwd=self.cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )

            line_q: "queue.Queue[str | None]" = queue.Queue()
            stderr_q: "queue.Queue[str | None]" = queue.Queue()

            def _pump_stdout(stream) -> None:
                try:
                    for line in iter(stream.readline, ""):
                        line = line.rstrip("\r\n")
                        if line:
                            line_q.put(line)
                finally:
                    line_q.put(None)  # EOF 哨兵

            def _pump_stderr(stream) -> None:
                try:
                    for line in iter(stream.readline, ""):
                        line = line.rstrip("\r\n")
                        if line:
                            stderr_q.put(line)
                finally:
                    stderr_q.put(None)

            th_out = threading.Thread(
                target=_pump_stdout, args=(self._proc.stdout,), daemon=True
            )
            th_err = threading.Thread(
                target=_pump_stderr, args=(self._proc.stderr,), daemon=True
            )
            th_out.start()
            th_err.start()

            done_emitted = False
            while True:
                try:
                    line = line_q.get(timeout=self.idle_timeout)
                except queue.Empty:
                    # idle 超时：CLI 长时间无输出，视为卡死，收 stderr 退出。
                    stderr_tail = self._drain(stderr_q)
                    yield AgentEvent(
                        kind="error",
                        error=(
                            f"claude CLI 超时（{self.idle_timeout}s 无输出）。"
                            f" stderr: {stderr_tail[:500]}"
                        ),
                    )
                    return

                if line is None:
                    # stdout EOF：CLI 退出。等子进程 + 收 stderr。
                    break

                # 逐行解析。
                try:
                    evt = json.loads(line)
                except json.JSONDecodeError:
                    # 非 JSON 行（CLI 偶发打印）：忽略，但保留可观测。
                    continue

                if not isinstance(evt, dict):
                    continue

                # 捕获 session_id（顶层优先；system.init 最权威，多数事件都带）。
                sid = evt.get("session_id")
                if isinstance(sid, str) and sid:
                    self._last_session_id = sid
                # system.init 显式刷新（确保 resume 场景也能捕获）。
                if evt.get("type") == "system" and evt.get("subtype") == "init":
                    isid = evt.get("session_id")
                    if isinstance(isid, str) and isid:
                        self._last_session_id = isid

                for agent_ev in translate_event(evt):
                    if agent_ev.kind == "done":
                        done_emitted = True
                    yield agent_ev

                # 墙钟超时检查（每次取到新行后检查）。
                if time.monotonic() - start_time > self.total_timeout:
                    stderr_tail = self._drain(stderr_q)
                    yield AgentEvent(
                        kind="error",
                        error=(
                            f"claude CLI 超过总超时 {self.total_timeout}s。"
                            f" stderr: {stderr_tail[:500]}"
                        ),
                    )
                    return

            # 等待子进程退出与线程结束。EOF 已到，进程应秒退；10s 不退视为异常。
            try:
                rc = self._proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                rc = -1
            th_out.join(timeout=5)
            th_err.join(timeout=5)

            # CLI 异常退出且未发 done：补一条 error（含 stderr 尾部）。
            if not done_emitted:
                stderr_tail = self._drain(stderr_q)
                rc_desc = describe_exit_code(rc)
                # rc != 0/1 且非超时 → 大概率是 CLI 自身崩溃，标记 crash=True 可重试
                is_crash = rc not in (0, 1) and rc != -1
                yield AgentEvent(
                    kind="error",
                    is_error=True,
                    crash=is_crash,
                    error=(
                        f"claude CLI 异常退出：{rc_desc}。"
                        f" stderr: {stderr_tail[:500]}"
                    ),
                )
        except FileNotFoundError:
            # Windows 上即使文件存在，Popen 也可能因以下原因报 FileNotFoundError：
            # - CLI 正在自动更新，exe 被短暂锁定/替换
            # - 杀毒软件实时扫描大文件（232MB）时短暂拦截
            # - 依赖的 DLL 缺失或被锁定
            # - 系统负载过高导致 CreateProcess 超时
            # 这些都是瞬态的，标记 crash=True 供上游重试。
            yield AgentEvent(
                kind="error",
                is_error=True,
                crash=True,
                error=(
                    f"找不到或无法执行 claude CLI：{cli_path}。"
                    f" 文件可能被暂时锁定（自动更新/杀毒扫描），"
                    f" 可通过环境变量 CLAUDE_CLI 指定其他路径。"
                    f" 若确认文件存在，重试通常可恢复。"
                ),
            )
        except Exception as exc:  # noqa: BLE001 - 顶层兜底，必须产 error 让调用方收尾
            yield AgentEvent(kind="error", error=f"{type(exc).__name__}: {exc}")
        finally:
            if self._proc is not None and self._proc.poll() is None:
                try:
                    self._proc.kill()
                except Exception:  # noqa: BLE001
                    pass

    def cancel(self) -> None:
        """从外部终止正在运行的 claude CLI 子进程。"""
        if self._proc is not None and self._proc.poll() is None:
            try:
                self._proc.kill()
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # 内部
    # ------------------------------------------------------------------ #
    @staticmethod
    def _drain(q: "queue.Queue[str | None]") -> str:
        """非阻塞取出队列中所有残余行，拼成字符串（保留**尾部** ~2000 字符）。

        CLI 失败的真因（堆栈/错误信息）通常在 stderr 尾部，因此保留尾部而非头部。
        若总长超过 2000 字符，在保留内容前加截断标记。
        """
        chunks: list[str] = []
        while True:
            try:
                item = q.get_nowait()
            except queue.Empty:
                break
            if item is None:
                continue
            chunks.append(item)
        if not chunks:
            return ""
        total = sum(len(c) for c in chunks) + max(0, len(chunks) - 1)  # 含 \n
        joined = "\n".join(chunks)
        if total <= 2000:
            return joined
        tail = joined[-2000:]
        return f"…(truncated, {total} chars total)…\n{tail}"
