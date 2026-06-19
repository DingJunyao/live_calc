"""Spike 探针：验证 subprocess 调 claude CLI 的 stream-json + MCP + resume + 代理 env。

用法：
    # 首次跑（无 session）
    uv run python spikes/agent_cli_probe.py

    # resume 跑（带前次 session_id，新 prompt）
    RESUME_SESSION=<session_id> NEXT_PROMPT="把不合理的改成 5" \
        uv run python spikes/agent_cli_probe.py

关键点：
- 必须 pop CLAUDECODE，否则 CLI 拒绝嵌套启动。
- 用 --include-partial-messages 观察 partial text 事件。
- stdout 逐行读 stream-json，stderr 单独线程转储。
"""
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

CWD = Path(__file__).resolve().parent
BACKEND = CWD.parent
CLI = os.environ.get("CLAUDE_CLI", "claude")

RESUME_SESSION = os.environ.get("RESUME_SESSION", "").strip()
DEFAULT_PROMPT = "用 db_read 查一下表里有哪些单位，然后告诉我你觉得哪个 weight_per_unit 不合理。"
NEXT_PROMPT = os.environ.get("NEXT_PROMPT", "把不合理的那个 weight_per_unit 改成 5，说说你的依据。")
PROMPT = NEXT_PROMPT if RESUME_SESSION else DEFAULT_PROMPT

env = os.environ.copy()
# 关键：claude CLI 在被另一个 claude 进程调用时会拒绝启动（检测 CLAUDECODE）。
env.pop("CLAUDECODE", None)
env["PYTHONIOENCODING"] = "utf-8"

cmd = [
    CLI, "-p", PROMPT,
    "--output-format", "stream-json",
    "--include-partial-messages",
    "--verbose",
    "--mcp-config", str(CWD / "mcp_config.json"),
    "--strict-mcp-config",
    "--allowedTools", "mcp__fake_db__db_read",
]
if RESUME_SESSION:
    cmd += ["--resume", RESUME_SESSION]

print("CMD:", " ".join(cmd), flush=True)
print("PROMPT:", PROMPT, flush=True)
print("ANTHROPIC_BASE_URL:", env.get("ANTHROPIC_BASE_URL", "<unset>"), flush=True)
print("ANTHROPIC_AUTH_TOKEN set:", bool(env.get("ANTHROPIC_AUTH_TOKEN")), flush=True)
sys.stdout.flush()

proc = subprocess.Popen(
    cmd, cwd=str(BACKEND), env=env,
    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, encoding="utf-8", errors="replace", bufsize=1,
)

# 完整事件落盘（utf-8），方便脱敏后引用，规避控制台 GBK 乱码
events_jsonl = CWD / ("events_resume.jsonl" if RESUME_SESSION else "events_first.jsonl")
if events_jsonl.exists():
    events_jsonl.unlink()
evl_fh = events_jsonl.open("w", encoding="utf-8")

event_types = []
events_raw = []
partial_text_sample = None
tool_use_seen = []
tool_result_seen = []
result_event = None
session_id_seen = None


def _summarize(evt):
    """记录每个事件的关键字段，但避免打印完整 token/敏感内容。"""
    t = evt.get("type")
    event_types.append(t)
    # 抓 session id（system 事件里）
    global session_id_seen
    if t == "system":
        session_id_seen = evt.get("session_id")
        return ("session_id=%s subtype=%s" % (
            evt.get("session_id"), evt.get("subtype")))
    # assistant 消息：可能有 content 数组
    if t == "assistant":
        msg = evt.get("message", {})
        sid = msg.get("id")
        parts = []
        for blk in msg.get("content", []):
            bt = blk.get("type")
            if bt == "text":
                txt = (blk.get("text") or "")
                parts.append("text(%d chars): %s" % (len(txt), txt[:120]))
            elif bt == "tool_use":
                tool_use_seen.append(blk.get("name"))
                parts.append("tool_use name=%s input=%s" % (
                    blk.get("name"),
                    json.dumps(blk.get("input", {}), ensure_ascii=False)[:160]))
            else:
                parts.append("blk type=%s" % bt)
        return "msg_id=%s [%s]" % (sid, " | ".join(parts))
    if t == "user":
        msg = evt.get("message", {})
        parts = []
        for blk in msg.get("content", []):
            if blk.get("type") == "tool_result":
                c = blk.get("content")
                if isinstance(c, list):
                    txt = " ".join(
                        (b.get("text", "") if isinstance(b, dict) else str(b))
                        for b in c)
                else:
                    txt = str(c)
                tool_result_seen.append(txt[:200])
                parts.append("tool_result(%d chars): %s" % (len(txt), txt[:160]))
            else:
                parts.append("blk=%s" % blk.get("type"))
        return "[%s]" % " | ".join(parts) if parts else "(empty)"
    if t == "result":
        global result_event
        result_event = evt
        return "subtype=%s cost_usd=%s duration_ms=%s is_error=%s" % (
            evt.get("subtype"), evt.get("total_cost_usd"),
            evt.get("duration_ms"), evt.get("is_error"))
    # stream_event: claude CLI 把 Anthropic SSE 事件包了一层，真正类型在 evt["event"]。
    if t == "stream_event":
        inner = evt.get("event") or {}
        it = inner.get("type", "?")
        # content_block_delta / partial text 增量
        if it == "content_block_delta":
            delta = inner.get("delta") or {}
            if delta.get("type") == "text_delta":
                global partial_text_sample
                if partial_text_sample is None:
                    partial_text_sample = delta.get("text", "")[:60]
                return "inner=%s delta.text=%r" % (it, delta.get("text", "")[:30])
            return "inner=%s delta=%s" % (it, json.dumps(delta, ensure_ascii=False)[:100])
        # 别的常见 inner 类型只记类型
        return "inner.type=%s" % it
    return "keys=%s" % ",".join(evt.keys())


def read_stdout():
    for line in iter(proc.stdout.readline, ""):
        line = line.rstrip("\r\n")
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            print("RAW(non-json):", line[:200], flush=True)
            continue
        events_raw.append(evt)
        try:
            evl_fh.write(json.dumps(evt, ensure_ascii=False) + "\n")
            evl_fh.flush()
        except Exception:
            pass
        try:
            summ = _summarize(evt)
        except Exception as e:
            summ = "<summarize error: %r>" % e
        print("[%s] %s" % (evt.get("type"), summ), flush=True)


def read_stderr():
    for line in iter(proc.stderr.readline, ""):
        line = line.rstrip("\r\n")
        if line:
            print("STDERR:", line[:300], flush=True)


threading.Thread(target=read_stdout, daemon=True).start()
threading.Thread(target=read_stderr, daemon=True).start()

rc = proc.wait()
print("\n=== exit code:", rc, "===", flush=True)
print("=== event_types (seq) ===", event_types, flush=True)
print("=== tool_use seen ===", tool_use_seen, flush=True)
print("=== tool_result seen ===", tool_result_seen, flush=True)
print("=== partial_text sample ===", repr(partial_text_sample), flush=True)
print("=== session_id (from system) ===", session_id_seen, flush=True)
print("=== result event ===",
      json.dumps(result_event, ensure_ascii=False) if result_event else None,
      flush=True)

# 把首次跑的 session_id 落盘，方便 resume
if session_id_seen and not RESUME_SESSION:
    (CWD / "last_session.txt").write_text(session_id_seen, encoding="utf-8")
    print("=== saved last_session.txt ===", session_id_seen, flush=True)
