# 生计 - 生活成本计算器
from __future__ import annotations

import json
from pathlib import Path

_DEFAULT_APP_INFO = {
    "name": "生计 - 生活成本计算器",
    "shortName": "生计",
    "version": "0.0.0",
    "description": "记录商品价格、计算烹饪与生活成本",
    "copyright": "Copyright © 2026 DingJunyao",
    "repository": "https://github.com/DingJunyao/live_calc",
    "homepage": "https://github.com/DingJunyao/live_calc",
    "authorHomepage": "https://4ading.com",
}


def _load_app_info() -> dict:
    """读取仓库根目录的 app-info.json，作为应用身份与版本的唯一来源。"""
    start = Path(__file__).resolve().parent
    candidates = (
        start / "app-info.json",
        start.parent / "app-info.json",
        start.parent.parent / "app-info.json",
    )
    for candidate in candidates:
        try:
            if not candidate.is_file():
                continue
            data = json.loads(candidate.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("version"):
                return data
        except (OSError, ValueError):
            continue
    return dict(_DEFAULT_APP_INFO)


APP_INFO = _load_app_info()
__version__ = APP_INFO["version"]
