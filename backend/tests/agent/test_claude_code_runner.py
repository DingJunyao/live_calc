"""ClaudeCodeRunner 单元测试。

策略：用 spike 录制的真实 jsonl 回放 + 手造覆盖各事件形态，喂给纯函数
``translate_event`` / ``build_cmd`` / ``build_env``，**不真调 CLI**（省钱）。
真调留 Task 9。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.services.agent.claude_code_runner import (
    ClaudeCodeRunner,
    _coerce_tool_result_content,
    build_cmd,
    build_env,
    translate_event,
)
from app.services.agent.runner import AgentEvent, AgentRunner

SPIKES_DIR = Path(__file__).resolve().parents[2] / "spikes"
EVENTS_FIRST = SPIKES_DIR / "events_first.jsonl"
EVENTS_RESUME = SPIKES_DIR / "events_resume.jsonl"


# ---------------------------------------------------------------------- #
# AgentRunner 协议：ClaudeCodeRunner 是否满足（runtime_checkable Protocol）
# ---------------------------------------------------------------------- #
def test_claude_code_runner_satisfies_protocol():
    runner = ClaudeCodeRunner(
        mcp_config_path="mcp.json", allowed_tools=["mcp__x__y"], cwd="."
    )
    # Protocol 是 runtime_checkable，仅检查方法/属性存在，不检查签名。
    assert isinstance(runner, AgentRunner)
    assert runner.last_session_id is None  # 初始未捕获


# ---------------------------------------------------------------------- #
# build_cmd
# ---------------------------------------------------------------------- #
def test_build_cmd_minimal_has_required_flags(monkeypatch):
    monkeypatch.delenv("CLAUDE_CLI", raising=False)
    cmd = build_cmd(
        prompt="hi",
        mcp_config_path="/abs/mcp.json",
        allowed_tools=["mcp__fake_db__db_read"],
        cwd="/proj",
    )
    # 必加 flag 全在。
    for flag in (
        "-p",
        "--output-format",
        "stream-json",
        "--include-partial-messages",
        "--verbose",
        "--strict-mcp-config",
        "--mcp-config",
        "--allowedTools",
    ):
        assert flag in cmd, f"missing flag: {flag}"
    assert cmd[0] == "claude"
    # prompt 透传。
    assert "hi" in cmd
    # allowedTools 逗号拼接。
    assert "mcp__fake_db__db_read" in cmd
    # 默认无 resume / budget。
    assert "--resume" not in cmd
    assert "--max-budget-usd" not in cmd
    # mcp_config 绝对路径原样保留（--mcp-config 紧跟的值）。
    mcp_idx = cmd.index("--mcp-config")
    assert cmd[mcp_idx + 1].endswith("mcp.json")


def test_build_cmd_relative_mcp_resolved_against_cwd(tmp_path):
    rel = "config/mcp.json"
    cwd = str(tmp_path)
    cmd = build_cmd(
        prompt="p",
        mcp_config_path=rel,
        allowed_tools=["t"],
        cwd=cwd,
    )
    resolved = str((tmp_path / rel).resolve())
    assert resolved in cmd


def test_build_cmd_with_resume_and_budget():
    cmd = build_cmd(
        prompt="p",
        mcp_config_path="/mcp.json",
        allowed_tools=["t1", "t2"],
        resume_session_id="sess-123",
        max_budget_usd=0.5,
        cwd="/proj",
    )
    assert "--resume" in cmd
    assert "sess-123" in cmd
    assert "--max-budget-usd" in cmd
    assert "0.5" in cmd
    # 多工具逗号拼接。
    assert "t1,t2" in cmd


def test_build_cmd_cli_env_override(monkeypatch):
    monkeypatch.setenv("CLAUDE_CLI", "/usr/local/bin/claude")
    cmd = build_cmd(
        prompt="p",
        mcp_config_path="/mcp.json",
        allowed_tools=["t"],
        cwd="/proj",
    )
    assert cmd[0] == "/usr/local/bin/claude"


def test_build_cmd_explicit_cli_wins_over_env(monkeypatch):
    monkeypatch.setenv("CLAUDE_CLI", "from-env")
    cmd = build_cmd(
        prompt="p",
        mcp_config_path="/mcp.json",
        allowed_tools=["t"],
        cli="explicit-cli",
        cwd="/proj",
    )
    assert cmd[0] == "explicit-cli"


# ---------------------------------------------------------------------- #
# build_env
# ---------------------------------------------------------------------- #
def test_build_env_pops_claudecode(monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    env = build_env()
    assert "CLAUDECODE" not in env


def test_build_env_utf8(monkeypatch):
    monkeypatch.delenv("PYTHONIOENCODING", raising=False)
    env = build_env()
    assert env["PYTHONIOENCODING"] == "utf-8"


def test_build_env_inherits_proxy_vars(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://proxy.example/v1")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "tok-abc")
    env = build_env()
    assert env["ANTHROPIC_BASE_URL"] == "https://proxy.example/v1"
    assert env["ANTHROPIC_AUTH_TOKEN"] == "tok-abc"


def test_build_env_extra_env_overrides(monkeypatch):
    monkeypatch.setenv("FOO", "orig")
    env = build_env({"FOO": "new", "NEW": "val"})
    assert env["FOO"] == "new"
    assert env["NEW"] == "val"


# ---------------------------------------------------------------------- #
# _coerce_tool_result_content：两种 content 形态
# ---------------------------------------------------------------------- #
def test_coerce_tool_result_list_form():
    content = [{"type": "text", "text": "hello"}, {"type": "text", "text": " world"}]
    assert _coerce_tool_result_content(content) == "hello world"


def test_coerce_tool_result_string_form():
    # spike events_first.jsonl 实测形态：content 是裸字符串。
    assert _coerce_tool_result_content('{"result":"x"}') == '{"result":"x"}'


def test_coerce_tool_result_none_and_dict():
    assert _coerce_tool_result_content(None) == ""
    assert "k" in _coerce_tool_result_content({"k": "v"})


# ---------------------------------------------------------------------- #
# translate_event：手造覆盖各事件类型
# ---------------------------------------------------------------------- #
def test_translate_stream_event_text_delta():
    evt = {
        "type": "stream_event",
        "event": {
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": "你好"},
        },
    }
    out = translate_event(evt)
    assert len(out) == 1
    assert out[0].kind == "text_delta"
    assert out[0].text == "你好"


def test_translate_stream_event_non_text_delta_ignored():
    evt = {
        "type": "stream_event",
        "event": {
            "type": "content_block_delta",
            "delta": {"type": "input_json_delta", "partial_json": "..."},
        },
    }
    assert translate_event(evt) == []


def test_translate_stream_event_other_inner_types_ignored():
    for inner_type in ("message_start", "content_block_start", "message_stop", "ping"):
        evt = {"type": "stream_event", "event": {"type": inner_type}}
        assert translate_event(evt) == []


def test_translate_assistant_event_only_emits_tool_use_not_text():
    """B-1：assistant 事件**只**产 tool_use，不产 text_delta（text 块内容已被
    stream_event 的 text_delta 完整覆盖，两者都产会导致前端文本翻倍）。"""
    evt = {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "text", "text": "我先查一下。"},
                {
                    "type": "tool_use",
                    "id": "call_abc",
                    "name": "mcp__fake_db__db_read",
                    "input": {"sql": "SELECT * FROM units"},
                },
            ]
        },
    }
    out = translate_event(evt)
    # 只产 tool_use，不产 text_delta。
    assert [e.kind for e in out] == ["tool_use"]
    assert out[0].tool_name == "mcp__fake_db__db_read"
    assert out[0].tool_use_id == "call_abc"
    assert out[0].tool_input == {"sql": "SELECT * FROM units"}
    # 明确断言没有任何 text_delta 事件。
    assert all(e.kind != "text_delta" for e in out)


def test_translate_assistant_empty_content():
    evt = {"type": "assistant", "message": {"content": []}}
    assert translate_event(evt) == []


def test_translate_user_tool_result_string_form():
    # spike events_first.jsonl 实测形态：content 是裸 JSON 字符串。
    evt = {
        "type": "user",
        "message": {
            "content": [
                {
                    "tool_use_id": "call_abc",
                    "type": "tool_result",
                    "content": '{"result":"id|unit_name\n1|个|100"}',
                }
            ]
        },
    }
    out = translate_event(evt)
    assert len(out) == 1
    assert out[0].kind == "tool_result"
    assert out[0].tool_use_id == "call_abc"
    assert "id|unit_name" in out[0].tool_result


def test_translate_user_tool_result_list_form():
    evt = {
        "type": "user",
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "x",
                    "content": [
                        {"type": "text", "text": "part1-"},
                        {"type": "text", "text": "part2"},
                    ],
                }
            ]
        },
    }
    out = translate_event(evt)
    assert len(out) == 1
    assert out[0].tool_result == "part1-part2"


def test_translate_result_success():
    evt = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "total_cost_usd": 0.044017799999999996,
        "permission_denials": [],
        "session_id": "sess-xyz",
    }
    out = translate_event(evt)
    assert len(out) == 1
    done = out[0]
    assert done.kind == "done"
    assert done.is_error is False
    assert done.cost_usd == pytest.approx(0.044017799999999996)
    assert done.permission_denials == []


def test_translate_result_error_with_denials():
    evt = {
        "type": "result",
        "subtype": "error",
        "is_error": True,
        "total_cost_usd": 0.01,
        "permission_denials": [{"tool": "Bash", "reason": "denied"}],
    }
    out = translate_event(evt)
    assert out[0].kind == "done"
    assert out[0].is_error is True
    assert out[0].cost_usd == pytest.approx(0.01)
    assert len(out[0].permission_denials) == 1
    assert out[0].error == "error"


def test_translate_result_subtype_error_forces_is_error():
    # is_error 缺失但 subtype=error 仍判错。
    evt = {"type": "result", "subtype": "error"}
    out = translate_event(evt)
    assert out[0].is_error is True


def test_translate_system_init_no_event():
    # system.init 不直接产事件（session_id 由 Runner 在主循环捕获）。
    evt = {
        "type": "system",
        "subtype": "init",
        "session_id": "abc",
        "tools": [],
    }
    assert translate_event(evt) == []


def test_translate_system_hook_events_ignored():
    evt = {"type": "system", "subtype": "hook_started", "session_id": "abc"}
    assert translate_event(evt) == []


def test_translate_unknown_type_ignored():
    assert translate_event({"type": "whatever"}) == []


# ---------------------------------------------------------------------- #
# translate_event：用 spike 真实 jsonl 回放，验证聚合正确性
# ---------------------------------------------------------------------- #
def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        pytest.skip(f"spike jsonl 不存在：{path}")
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


@pytest.mark.parametrize("jsonl_path", [EVENTS_FIRST, EVENTS_RESUME])
def test_translate_real_jsonl_aggregates_text(jsonl_path):
    """回放真实 jsonl：text_delta 聚合出非空文本，至少一个 tool_use / tool_result。"""
    events = _load_jsonl(jsonl_path)
    text_parts: list[str] = []
    tool_use_count = 0
    tool_result_count = 0
    done_count = 0
    for evt in events:
        for ae in translate_event(evt):
            if ae.kind == "text_delta":
                text_parts.append(ae.text)
            elif ae.kind == "tool_use":
                tool_use_count += 1
            elif ae.kind == "tool_result":
                tool_result_count += 1
            elif ae.kind == "done":
                done_count += 1
    full = "".join(text_parts)
    assert full, "聚合文本不应为空"
    assert tool_use_count >= 1, "至少一次 tool_use"
    assert tool_result_count >= 1, "至少一次 tool_result"
    assert done_count == 1, "恰好一个 done"


def test_translate_real_jsonl_session_id_on_system_init():
    """system.init 顶层带 session_id（Runner 主循环会捕获，这里只断言事件里有）。"""
    events = _load_jsonl(EVENTS_FIRST)
    init_evts = [
        e for e in events if e.get("type") == "system" and e.get("subtype") == "init"
    ]
    assert init_evts, "events_first.jsonl 应含 system.init"
    assert init_evts[0].get("session_id"), "system.init 必须带 session_id"


def test_translate_real_jsonl_result_has_cost():
    """events_resume.jsonl 的 result 事件带 total_cost_usd，done.cost_usd 应解析出 float。"""
    events = _load_jsonl(EVENTS_RESUME)
    result_evts = [e for e in events if e.get("type") == "result"]
    assert result_evts
    done_events: list[AgentEvent] = []
    for e in result_evts:
        done_events.extend(translate_event(e))
    costs = [d.cost_usd for d in done_events if d.cost_usd is not None]
    assert costs, "应至少有一个 done 携带 cost_usd"
    assert all(isinstance(c, float) for c in costs)


# ---------------------------------------------------------------------- #
# Runner：构造 + last_session_id 初始态
# ---------------------------------------------------------------------- #
def test_runner_construct_defaults():
    runner = ClaudeCodeRunner(
        mcp_config_path="/mcp.json",
        allowed_tools=["mcp__x__y"],
        cwd="/proj",
    )
    assert runner.last_session_id is None
    assert runner.idle_timeout == 120.0
    assert runner.total_timeout == 600.0
    assert runner.max_budget_usd is None
    assert runner.allowed_tools == ["mcp__x__y"]
    assert runner.extra_env is None


def test_runner_construct_with_all_params():
    runner = ClaudeCodeRunner(
        mcp_config_path="/mcp.json",
        allowed_tools=["t"],
        cwd="/proj",
        idle_timeout=30.0,
        total_timeout=300.0,
        max_budget_usd=0.1,
        extra_env={"EXTRA": "1"},
        cli="/opt/claude",
    )
    assert runner.idle_timeout == 30.0
    assert runner.total_timeout == 300.0
    assert runner.max_budget_usd == 0.1
    assert runner.extra_env == {"EXTRA": "1"}
    assert runner.cli == "/opt/claude"


# ---------------------------------------------------------------------- #
# Runner.run：不真调 CLI，用 monkeypatch 替换 subprocess.Popen 喂回放数据
# ---------------------------------------------------------------------- #
class _FakePopen:
    """模拟 subprocess.Popen：构造时喂入预设的 stdout 行流。"""

    def __init__(self, cmd, cwd=None, env=None, stdout=None, stderr=None,
                 text=False, encoding=None, errors=None, bufsize=0):
        self.cmd = cmd
        self.env = env
        # 测试用例通过 _FakePopen.script 注入待读取的行。
        lines = getattr(_FakePopen, "_script", [])
        self._stdout_lines = list(lines)
        self._stderr_lines = list(getattr(_FakePopen, "_stderr_script", []))
        self.stdout = self
        self.stderr = self
        self._rc = 0
        self._returned = False

    # 文件式 readline 接口（被 iter(stream.readline, "") 使用）。
    def readline(self):
        if self._stdout_lines:
            return self._stdout_lines.pop(0) + "\n"
        return ""  # EOF

    def poll(self):
        return 0 if self._returned else None

    def wait(self, timeout=None):
        self._returned = True
        return self._rc

    def kill(self):
        self._returned = True


def test_runner_run_translates_stream_and_captures_session(monkeypatch):
    # 验证 build_env pop 了 CLAUDECODE（先 set，确认 pop 生效）。
    monkeypatch.setenv("CLAUDECODE", "1")

    script = [
        json.dumps(
            {
                "type": "system",
                "subtype": "init",
                "session_id": "sess-init-123",
                "tools": ["mcp__fake_db__db_read"],
            }
        ),
        json.dumps(
            {
                "type": "stream_event",
                "event": {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": "hello "},
                },
            }
        ),
        json.dumps(
            {
                "type": "stream_event",
                "event": {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": "world"},
                },
            }
        ),
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "call_1",
                            "name": "mcp__fake_db__db_read",
                            "input": {"sql": "SELECT 1"},
                        }
                    ]
                },
            }
        ),
        json.dumps(
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "call_1",
                            "content": "ok",
                        }
                    ]
                },
            }
        ),
        json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "total_cost_usd": 0.02,
                "permission_denials": [],
            }
        ),
    ]
    _FakePopen._script = script
    _FakePopen._stderr_script = []
    monkeypatch.setattr(
        "app.services.agent.claude_code_runner.subprocess.Popen", _FakePopen
    )

    runner = ClaudeCodeRunner(
        mcp_config_path="/mcp.json",
        allowed_tools=["mcp__fake_db__db_read"],
        cwd="/proj",
        idle_timeout=5.0,
    )
    events = list(runner.run("hi"))

    # session_id 从 system.init 捕获。
    assert runner.last_session_id == "sess-init-123"
    # text_delta 聚合。
    text = "".join(e.text for e in events if e.kind == "text_delta")
    assert text == "hello world"
    # tool_use / tool_result / done 都在。
    kinds = [e.kind for e in events]
    assert "tool_use" in kinds
    assert "tool_result" in kinds
    done = [e for e in events if e.kind == "done"]
    assert len(done) == 1
    assert done[0].cost_usd == pytest.approx(0.02)
    assert done[0].is_error is False


def test_runner_run_replay_real_jsonl_first(monkeypatch):
    """用真实 events_first.jsonl 喂给 _FakePopen，验证 last_session_id 与聚合。"""
    events = _load_jsonl(EVENTS_FIRST)
    script = [json.dumps(e, ensure_ascii=False) for e in events]
    _FakePopen._script = script
    _FakePopen._stderr_script = []
    monkeypatch.setattr(
        "app.services.agent.claude_code_runner.subprocess.Popen", _FakePopen
    )

    runner = ClaudeCodeRunner(
        mcp_config_path="/mcp.json",
        allowed_tools=["mcp__fake_db__db_read"],
        cwd="/proj",
        idle_timeout=5.0,
    )
    out = list(runner.run("probe"))
    # session_id 与 system.init 一致。
    init_evts = [e for e in events if e.get("type") == "system" and e.get("subtype") == "init"]
    assert init_evts
    assert runner.last_session_id == init_evts[0]["session_id"]
    # 必有 done。
    assert any(e.kind == "done" for e in out)


def test_runner_run_emits_error_on_missing_cli(monkeypatch):
    """subprocess.Popen 抛 FileNotFoundError → 产 error 事件。"""

    def _raise(*a, **kw):
        raise FileNotFoundError(2, "No such file", "claude")

    monkeypatch.setattr(
        "app.services.agent.claude_code_runner.subprocess.Popen", _raise
    )
    runner = ClaudeCodeRunner(
        mcp_config_path="/mcp.json", allowed_tools=["t"], cwd="."
    )
    events = list(runner.run("hi"))
    assert events and events[-1].kind == "error"
    assert "claude" in events[-1].error.lower()


def test_runner_run_emits_error_on_idle_timeout(monkeypatch):
    """B-2：stdout 无输出导致 queue.get(idle_timeout) 超时 → 产 error 事件。"""

    class _SilentPopen(_FakePopen):
        def readline(self):
            # 永不返回数据（也不返回 ""），让主循环 queue.get 超时。
            import time

            time.sleep(0.2)
            return ""  # 最终 EOF，但主循环会先因 idle_timeout 退出

    monkeypatch.setattr(
        "app.services.agent.claude_code_runner.subprocess.Popen", _SilentPopen
    )
    runner = ClaudeCodeRunner(
        mcp_config_path="/mcp.json",
        allowed_tools=["t"],
        cwd=".",
        idle_timeout=0.1,  # 极短 idle 超时，立即触发
        total_timeout=60.0,  # 总超时放宽，确保只触发 idle 路径
    )
    events = list(runner.run("hi"))
    assert events
    assert events[-1].kind == "error"
    assert "超时" in events[-1].error
    # idle 超时文案明确标注 idle_timeout 值。
    assert "0.1s 无输出" in events[-1].error


def test_runner_run_emits_error_on_total_timeout(monkeypatch):
    """B-2：墙钟超 total_timeout → 产 error 事件（即便有持续输出）。

    通过慢慢喂行（每行 0.05s）但 total_timeout 设极短，让墙钟先超。
    idle_timeout 放宽避免误触。
    """
    import time as _time

    class _SlowPopen(_FakePopen):
        def readline(self):
            _time.sleep(0.05)
            if self._stdout_lines:
                return self._stdout_lines.pop(0) + "\n"
            return ""

    _FakePopen._script = [
        json.dumps(
            {
                "type": "stream_event",
                "event": {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": "x"},
                },
            }
        ),
    ] * 50  # 持续输出，但 total_timeout 极短
    _FakePopen._stderr_script = []
    monkeypatch.setattr(
        "app.services.agent.claude_code_runner.subprocess.Popen", _SlowPopen
    )
    runner = ClaudeCodeRunner(
        mcp_config_path="/mcp.json",
        allowed_tools=["t"],
        cwd=".",
        idle_timeout=60.0,  # 放宽，确保只触发 total 路径
        total_timeout=0.1,  # 极短墙钟上限
    )
    events = list(runner.run("hi"))
    errs = [e for e in events if e.kind == "error"]
    assert errs, "应因墙钟超时产 error"
    assert "总超时" in errs[-1].error
    assert "0.1s" in errs[-1].error


def test_runner_run_resume_and_budget_flags_passed(monkeypatch):
    """resume + max_budget_usd 时，cmd 必须含对应 flag。"""
    captured: dict = {}

    class _CapPopen(_FakePopen):
        def __init__(self, cmd, **kw):
            captured["cmd"] = cmd
            captured["env"] = kw.get("env")
            super().__init__(cmd, **kw)

    _FakePopen._script = [
        json.dumps({"type": "result", "subtype": "success", "is_error": False})
    ]
    monkeypatch.setattr(
        "app.services.agent.claude_code_runner.subprocess.Popen", _CapPopen
    )

    runner = ClaudeCodeRunner(
        mcp_config_path="/mcp.json",
        allowed_tools=["t"],
        cwd="/proj",
        max_budget_usd=0.25,
    )
    list(runner.run("go", resume_session_id="sess-old"))
    cmd = captured["cmd"]
    assert "--resume" in cmd
    assert "sess-old" in cmd
    assert "--max-budget-usd" in cmd
    assert "0.25" in cmd
    # env pop 了 CLAUDECODE（即使外层 set 了）。
    assert "CLAUDECODE" not in captured["env"]
    assert captured["env"]["PYTHONIOENCODING"] == "utf-8"


def test_runner_run_abnormal_exit_emits_error(monkeypatch):
    """CLI 异常退出且未发 done → 补一条 error。"""

    class _NoDonePopen(_FakePopen):
        pass

    _FakePopen._script = [
        json.dumps(
            {
                "type": "stream_event",
                "event": {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": "x"},
                },
            }
        ),
        # 没有 result/done 就 EOF。
    ]
    _FakePopen._stderr_script = ["some stderr line"]
    monkeypatch.setattr(
        "app.services.agent.claude_code_runner.subprocess.Popen", _NoDonePopen
    )
    runner = ClaudeCodeRunner(
        mcp_config_path="/mcp.json", allowed_tools=["t"], cwd="."
    )
    events = list(runner.run("hi"))
    assert events[-1].kind == "error"
    assert "异常退出" in events[-1].error


# ---------------------------------------------------------------------- #
# B-1 回归：真实 jsonl 文本不应双份产出（stream 是唯一文本源，assistant 不产 text）
# ---------------------------------------------------------------------- #
def test_b1_no_double_text_emission_real_jsonl():
    """B-1：用 events_first.jsonl 真实行回放，断言「text_delta 聚合文本 ==
    result.result 文本」（result 携带最终完整文本，作为基准）。

    若 assistant 分支又产了一份 text_delta，聚合会变成 2 倍并包含重复段。
    events_first.jsonl 中 result.result 是 stream_text 的子串（stream 含一些
    assistant 内部推理前缀，但都来自唯一的 stream 源，不会重复），断言：
    (1) 聚合文本非空； (2) result.result 是聚合文本的子串；
    (3) 聚合文本长度 != 2 * result.result 长度（排除双份）。
    """
    events = _load_jsonl(EVENTS_FIRST)
    text_parts: list[str] = []
    result_text = None
    for evt in events:
        for ae in translate_event(evt):
            if ae.kind == "text_delta":
                text_parts.append(ae.text)
        if evt.get("type") == "result":
            result_text = evt.get("result")
    full = "".join(text_parts)
    assert full, "聚合文本非空"
    assert result_text, "result 事件应有 result 字段"
    # result 是 stream 唯一文本源的子串（stream 多了 assistant 内部推理）。
    assert result_text in full, "result 文本应是聚合文本的子串"
    # 关键反双份断言：聚合长度不应接近 2 倍 result 长度。
    # 实测：单份时 full 比 result 长约 14 字符；双份会 > 2 * len(result)。
    assert len(full) < 2 * len(result_text), (
        f"疑似双份产出：full={len(full)} result={len(result_text)}"
    )


def test_b1_assistant_text_block_skipped_unit():
    """B-1 单元：assistant 事件的 text 块被跳过，仅 tool_use 块产出。"""
    evt = {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "text", "text": "应被跳过的文本"},
                {"type": "text", "text": "另一段应被跳过的文本"},
                {
                    "type": "tool_use",
                    "id": "u1",
                    "name": "mcp__x__y",
                    "input": {"a": 1},
                },
            ]
        },
    }
    out = translate_event(evt)
    assert [e.kind for e in out] == ["tool_use"]
    assert all(e.kind != "text_delta" for e in out)
    assert out[0].tool_name == "mcp__x__y"


# ---------------------------------------------------------------------- #
# B-3 回归：stderr _drain 保留尾部而非头部
# ---------------------------------------------------------------------- #
def test_b3_drain_keeps_tail_with_truncation_marker():
    """B-3：超长 stderr 保留尾部 2000 字符，前置截断标记。"""
    import queue as _q

    q: "_q.Queue[str | None]" = _q.Queue()
    # 喂入 3000 字符：头部「H...」+ 尾部「TAIL_END_MARKER」。
    q.put("H" * 2980)
    q.put("TAIL_END_MARKER")  # 15 字符 + 1 \n = 2996 内容
    q.put(None)  # EOF 哨兵
    out = ClaudeCodeRunner._drain(q)
    assert "TAIL_END_MARKER" in out, "尾部应被保留"
    assert "H" * 2980 not in out, "头部不应被完整保留"
    assert "truncated" in out, "应有截断标记"
    assert out.startswith("…(truncated,")
    # 总字符数标注应正确（2980 + \n + 15 = 2996）。
    assert "2996 chars total" in out


def test_b3_drain_keeps_everything_when_short():
    """B-3：短 stderr 全保留，无截断标记。"""
    import queue as _q

    q: "_q.Queue[str | None]" = _q.Queue()
    q.put("line1")
    q.put("line2")
    out = ClaudeCodeRunner._drain(q)
    assert out == "line1\nline2"
    assert "truncated" not in out


def test_b3_drain_empty():
    """B-3：空队列返回空字符串。"""
    import queue as _q

    q: "_q.Queue[str | None]" = _q.Queue()
    assert ClaudeCodeRunner._drain(q) == ""


# ---------------------------------------------------------------------- #
# B-5 回归：每次 run() 重置 _last_session_id
# ---------------------------------------------------------------------- #
def test_b5_session_id_reset_each_run(monkeypatch):
    """B-5：run() 开头应把 _last_session_id 置 None，强制每次重新捕获。

    场景：第一次 run 捕获了 session-A；第二次 run 的 CLI 没发 system.init
    （模拟 --resume 失败），也不带顶层 session_id，此时 last_session_id 应为
    None 而非沿用旧的 session-A。
    """

    # 第一次脚本：正常 system.init 带 session-A。
    script_with_init = [
        json.dumps(
            {
                "type": "system",
                "subtype": "init",
                "session_id": "session-A",
                "tools": ["t"],
            }
        ),
        json.dumps({"type": "result", "subtype": "success", "is_error": False}),
    ]
    # 第二次脚本：无 system.init，无顶层 session_id（模拟 resume 失败）。
    script_no_init = [
        json.dumps({"type": "result", "subtype": "error", "is_error": True}),
    ]

    runner = ClaudeCodeRunner(
        mcp_config_path="/mcp.json", allowed_tools=["t"], cwd="."
    )

    _FakePopen._script = script_with_init
    _FakePopen._stderr_script = []
    monkeypatch.setattr(
        "app.services.agent.claude_code_runner.subprocess.Popen", _FakePopen
    )
    list(runner.run("first"))
    assert runner.last_session_id == "session-A", "第一次 run 应捕获 session-A"

    _FakePopen._script = script_no_init
    list(runner.run("second"))
    assert runner.last_session_id is None, (
        "B-5：第二次 run 无 session 信息时应为 None，而非沿用 session-A"
    )


def test_b5_session_id_captured_fresh_each_run(monkeypatch):
    """B-5：连续两次 run 各自捕获自己的新 session_id（即便不同）。"""
    script_a = [
        json.dumps(
            {"type": "system", "subtype": "init", "session_id": "A", "tools": []}
        ),
        json.dumps({"type": "result", "subtype": "success", "is_error": False}),
    ]
    script_b = [
        json.dumps(
            {"type": "system", "subtype": "init", "session_id": "B", "tools": []}
        ),
        json.dumps({"type": "result", "subtype": "success", "is_error": False}),
    ]
    runner = ClaudeCodeRunner(
        mcp_config_path="/mcp.json", allowed_tools=["t"], cwd="."
    )
    _FakePopen._stderr_script = []
    monkeypatch.setattr(
        "app.services.agent.claude_code_runner.subprocess.Popen", _FakePopen
    )

    _FakePopen._script = script_a
    list(runner.run("first"))
    assert runner.last_session_id == "A"

    _FakePopen._script = script_b
    list(runner.run("second"))
    assert runner.last_session_id == "B", "第二次 run 应捕获新 session-B 而非沿用 A"
