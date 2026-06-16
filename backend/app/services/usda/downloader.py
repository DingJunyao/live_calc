# backend/app/services/usda/downloader.py
"""抓 USDA FoodData Central 下载页直链，下载 zip，解析为食材列表。

参考 D:\\code\\HowToCook_json_organizer\\scripts\\build_usda_data.py 的抓取逻辑。
"""
import io
import json
import zipfile
import logging
import re

import httpx

from app.services.usda.parser import parse_usda_food, dedupe_foods

logger = logging.getLogger(__name__)

USDA_DOWNLOAD_PAGE = "https://fdc.nal.usda.gov/download-datasets.html"

# 数据集 → JSON zip 内顶层键 + data_type 标签
_DATASETS = {
    "foundation": ("FoundationFoods", "foundation"),
    "sr_legacy": ("SRLegacyFoods", "sr_legacy"),
}


def fetch_dataset_urls(page_url: str = USDA_DOWNLOAD_PAGE) -> dict[str, str]:
    """从 USDA 下载页抓取 Foundation + SR Legacy 的 JSON zip 直链。

    返回 {"foundation": url, "sr_legacy": url}。优先 JSON 格式，按文件名日期取最新。
    """
    resp = httpx.get(
        page_url,
        timeout=30.0,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        follow_redirects=True,
    )
    resp.raise_for_status()
    html = resp.text

    # 收集所有 .zip 链接（绝对 URL + 相对 /fdc-datasets/ 路径）
    zip_urls: list[str] = []
    for m in re.finditer(r'href="(https?://[^"]+\.zip)"', html):
        zip_urls.append(m.group(1))
    for m in re.finditer(r'href="(/fdc-datasets/[^"]+\.zip)"', html):
        zip_urls.append("https://fdc.nal.usda.gov" + m.group(1))

    # 按关键词归类
    candidates: dict[str, list[str]] = {name: [] for name in _DATASETS}
    for url in sorted(set(zip_urls)):
        url_lower = url.lower()
        for ds in _DATASETS:
            if ds in url_lower and url not in candidates[ds]:
                candidates[ds].append(url)

    def _extract_date(u: str) -> str:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", u)
        return m.group(1) if m else "0000-00-00"

    # 每个 dataset：优先 JSON，按日期取最新
    matched: dict[str, str] = {}
    for ds, urls in candidates.items():
        if not urls:
            logger.warning(f"未在下载页找到 {ds} 的 zip 链接")
            continue
        json_urls = [u for u in urls if "json" in u.rsplit("/", 1)[-1].lower()]
        preferred = json_urls if json_urls else urls
        preferred.sort(key=_extract_date, reverse=True)
        matched[ds] = preferred[0]
    return matched


def download_and_parse(url: str, top_key: str, data_type: str) -> list[dict]:
    """下载 zip → 读 JSON → 解析为食材 dict 列表（未去重）。

    兼容顶层 list 或 dict（尝试 top_key 及其驼峰变体），过滤非 dict / null 条目。
    """
    resp = httpx.get(url, timeout=600.0, follow_redirects=True)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        json_name = next(n for n in zf.namelist() if n.endswith(".json"))
        with zf.open(json_name) as f:
            data = json.load(f)

    # 定位食物数组
    raw_list: list = []
    if isinstance(data, list):
        raw_list = data
    elif isinstance(data, dict):
        # 尝试 top_key 及驼峰变体（FoundationFoods / foundationFoods）
        key_variants = [top_key, top_key[0].lower() + top_key[1:]] if top_key else []
        for key in key_variants:
            if key in data and isinstance(data[key], list):
                raw_list = data[key]
                logger.info(f"{data_type}: 数据集键名 {key}，{len(raw_list)} 条")
                break

    # 过滤非 dict / null 条目（USDA 数据偶有 null 元素）
    valid = [r for r in raw_list if isinstance(r, dict)]
    if len(valid) != len(raw_list):
        logger.warning(f"{data_type}: 原始 {len(raw_list)} 条，过滤非 dict/null 后 {len(valid)} 条")
    return [parse_usda_food(r, data_type=data_type) for r in valid]


def download_all(datasets: list[str] | None = None) -> list[dict]:
    """下载并合并多数据集，返回去重后的食材列表。"""
    datasets = datasets or list(_DATASETS.keys())
    urls = fetch_dataset_urls()
    all_foods: list[dict] = []
    for ds in datasets:
        top_key, data_type = _DATASETS[ds]
        if ds not in urls:
            logger.warning(f"未找到 {ds} 下载链接，跳过")
            continue
        all_foods.extend(download_and_parse(urls[ds], top_key, data_type))
    return dedupe_foods(all_foods)
