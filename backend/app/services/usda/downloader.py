# backend/app/services/usda/downloader.py
"""抓 USDA FoodData Central 下载页直链，下载 zip，解析为食材列表。

参考 D:\\code\\HowToCook_json_organizer\\scripts\\build_usda_data.py 的抓取逻辑。
"""
import io
import json
import zipfile
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from app.config import settings
from app.services.usda.parser import parse_usda_food, dedupe_foods

logger = logging.getLogger(__name__)

USDA_DOWNLOAD_PAGE = "https://fdc.nal.usda.gov/download-datasets.html"
# 完整浏览器 UA：USDA 的 WAF 会按 TLS 指纹 + UA 概率性切断非浏览器客户端，
# 半截 UA（缺 Chrome/Safari/Edg 标识）被当 bot 切断率显著升高
# （同库同窗口对照实测：完整 UA 4/6，半截 UA 1/6）。
USDA_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0"
)

# 指数退避参数：握手被切断既按 UA/TLS 指纹概率发生，也随网络窗口剧烈波动
# （好窗口单次近 100%，差窗口近 0%），故首轮并发抢成功、失败则退避等窗口恢复
_BACKOFF_BASE = 1.5
_BACKOFF_MAX = 30.0


def _make_client(
    timeout: float,
    follow_redirects: bool = True,
    connect_timeout: float | None = None,
) -> httpx.Client:
    """构造 USDA 下载用 httpx.Client：统一 UA + 可选代理 + 短握手超时。

    配 settings.usda_http_proxy 则走代理，留空走直连（并兼容 HTTPS_PROXY 等环境变量）。
    connect_timeout 单独控制握手阶段，握手被切断时能快速失败以触发重试。
    """
    ct = settings.usda_connect_timeout if connect_timeout is None else connect_timeout
    kwargs: dict = {
        "timeout": httpx.Timeout(ct, read=timeout, write=timeout, pool=timeout),
        "follow_redirects": follow_redirects,
        "headers": {"User-Agent": USDA_UA},
    }
    if settings.usda_http_proxy:
        kwargs["proxy"] = settings.usda_http_proxy
    return httpx.Client(**kwargs)


def _do_get(
    url: str, timeout: float, connect_timeout: float, follow_redirects: bool
) -> httpx.Response:
    """单次 GET：在连接关闭前读全响应体。失败时抛 httpx 异常交由上层分类重试。"""
    with _make_client(
        timeout, follow_redirects=follow_redirects, connect_timeout=connect_timeout
    ) as client:
        resp = client.get(url)
        resp.raise_for_status()
        _ = resp.content  # 在连接关闭前确保响应体已读入内存
        return resp


def _get_with_retry(
    url: str,
    *,
    timeout: float | None = None,
    retries: int | None = None,
    follow_redirects: bool = True,
) -> httpx.Response:
    """并发重试 GET，针对瞬时网络错误（TLS 握手被概率性切断 / 超时）。

    USDA 的 WAF 按完整浏览器 UA + TLS 指纹概率性切断非浏览器客户端，
    且切断率随网络窗口剧烈波动（好窗口单次近 100%，差窗口近 0%）。
    故每轮并发 concurrency 个握手（任一成功即返回），全失败则指数退避
    等窗口恢复再来，最多 ceil(retries/concurrency) 轮。
    确定性 HTTP 状态错误（4xx/5xx）不重试，立即抛出。
    """
    timeout = settings.usda_download_timeout if timeout is None else timeout
    retries = settings.usda_download_retries if retries is None else retries
    concurrency = max(1, settings.usda_download_concurrency)
    rounds = max(1, (retries + concurrency - 1) // concurrency)
    connect_timeout = settings.usda_connect_timeout

    last_exc: Exception | None = None
    for rnd in range(rounds):
        n = min(concurrency, retries - rnd * concurrency)
        if n <= 0:
            break
        with ThreadPoolExecutor(max_workers=n) as pool:
            futs = [
                pool.submit(_do_get, url, timeout, connect_timeout, follow_redirects)
                for _ in range(n)
            ]
            for fut in as_completed(futs):
                try:
                    return fut.result()
                except httpx.HTTPStatusError as e:
                    # 确定性错误：已连上服务器拿到响应，重试无意义，优先保留以便抛出
                    last_exc = e if not isinstance(last_exc, httpx.HTTPStatusError) else last_exc
                except httpx.TransportError as e:
                    if last_exc is None or isinstance(last_exc, httpx.HTTPStatusError):
                        last_exc = e
                    logger.warning("USDA 请求失败：%s: %s", type(e).__name__, str(e)[:120])
        # 确定性 HTTP 错误直接终止；网络瞬时错误则退避后重试（最后一轮除外）
        if isinstance(last_exc, httpx.HTTPStatusError):
            break
        if rnd < rounds - 1:
            sleep = min(_BACKOFF_BASE * (2 ** rnd), _BACKOFF_MAX)
            logger.info("USDA 第 %d/%d 轮并发全失败，%.1fs 后重试", rnd + 1, rounds, sleep)
            time.sleep(sleep)
    assert last_exc is not None
    raise last_exc

# 数据集 → JSON zip 内顶层键 + data_type 标签
_DATASETS = {
    "foundation": ("FoundationFoods", "foundation"),
    "sr_legacy": ("SRLegacyFoods", "sr_legacy"),
}


def fetch_dataset_urls(page_url: str = USDA_DOWNLOAD_PAGE) -> dict[str, str]:
    """从 USDA 下载页抓取 Foundation + SR Legacy 的 JSON zip 直链。

    返回 {"foundation": url, "sr_legacy": url}。优先 JSON 格式，按文件名日期取最新。
    """
    resp = _get_with_retry(page_url, timeout=30.0, follow_redirects=True)
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
    resp = _get_with_retry(url)  # 默认 timeout/retries 取自 settings
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
