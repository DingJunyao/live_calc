"""验证 ensure_administrative_regions 不被 first_run_init_recipes 条件卡住。

用静态分析断言 main.py 里 ensure_administrative_regions 的调用缩进
与 first_run 的 if/else 同级（无条件执行），而非嵌在 else 内。
"""
from pathlib import Path

MAIN_PY = Path(__file__).resolve().parents[2] / "app" / "main.py"


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def test_ensure_administrative_regions_not_nested_in_first_run_else():
    src = MAIN_PY.read_text(encoding="utf-8")
    lines = src.splitlines()

    if_line = next(i for i, ln in enumerate(lines) if "settings.first_run_init_recipes" in ln and "if " in ln)
    # 找包含 ensure_administrative_regions 调用的 try 块（通过注释定位）
    region_comment_line = next(i for i, ln in enumerate(lines) if "确保行政区划数据存在" in ln and i > if_line)
    # 下一行应该是 try:
    try_line = region_comment_line + 1
    ensure_line = next(i for i, ln in enumerate(lines) if "ensure_administrative_regions(db)" in ln)

    assert ensure_line > if_line, "ensure 调用应在 first_run 判断之后"
    # 检查 try 块与 if 语句同级，而非嵌在 else 内
    assert _indent(lines[try_line]) == _indent(lines[if_line]), (
        f"ensure_administrative_regions 的 try 块须在 first_run if/else 之外（缩进 {_indent(lines[try_line])} "
        f"应等于 if 缩进 {_indent(lines[if_line])}），当前嵌在条件块内——非首次启动库会跳过 seed"
    )
