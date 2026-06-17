# USDA 下载 SSL 握手失败修复

## 问题

管理员触发 USDA 数据下载（`POST /api/v1/usda/download`）时报错：

```
httpcore.ConnectError: [SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1081)
```

调用栈落在 `app/services/usda/downloader.py` 的 TLS 握手阶段（`start_tls`）即失败，连 HTTP 请求都没发出去。

## 根因

经四组对照实验定位（直连 `fdc.nal.usda.gov`，无代理，OpenSSL 3.0.20 / Python 3.14，同一时间窗口连续测）：

| 组合 | 结果 |
| ------ | ------ |
| urllib + **完整** UA（参考项目同款） | **4/6** |
| urllib + 半截 UA（原 downloader） | 1/6 |
| httpx + 完整 UA | 6/6 |
| httpx + 半截 UA | 6/6 |

两个结论：

1. **UA 是显著因素**：urllib 同库同窗口，唯一变量是 UA——完整 4/6、半截 1/6。USDA 的 WAF 按 TLS 指纹 + UA 概率性切断「非浏览器客户端」，半截 UA（`...AppleWebKit/537.36` 戛然而止，缺 `Chrome/... Safari/... Edg/...`）被当 bot，切断率飙升。**原 `downloader.py` 的 `USDA_UA` 就是半截的，这是被切断的代码侧主因。**
2. **httpx 无辜**：好窗口下 httpx 6/6，比 urllib 还稳；之前 0/6 是差窗口的锅，不是库的问题。无需换库、更不依赖外部 `curl`（跨系统不可靠）。

叠加放大因素：**网络窗口剧烈波动**——好窗口单次成功率近 100%，差窗口近 0%（httpx 都 0/6）。这是网络中间设备对 USDA 域名的 RST/丢包，与时机强相关，单靠任何单一纯 Python 配置都无法保证 100%。

参考实现 `D:\code\HowToCook_json_organizer\scripts\build_usda_data.py` 用的就是标准库 `urllib.request` + 完整浏览器 UA，能跑通——印证了完整 UA 的关键作用。

## 修复（纯 Python，跨平台）

### 1. downloader.py —— UA 完整化（核心）

`USDA_UA` 由半截改为完整 Edge 浏览器 UA（与参考项目一致）：

```python
USDA_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0"
)
```

这是降切断率的根本手段。

### 2. downloader.py —— httpx 并发重试 + 退避（兜窗口波动）

- `_make_client(timeout, follow_redirects, connect_timeout)`：统一 UA + 可选代理 + 短握手超时（`usda_connect_timeout`）快速失败以触发重试
- `_get_with_retry(url, ...)`：每轮并发 `usda_download_concurrency`（默认 5）个握手，任一成功即返回；全失败则指数退避（基数 1.5s、上限 30s）等窗口恢复再来，最多 `ceil(retries/concurrency)` 轮（默认 20 次 → 4 轮）。仅对 `httpx.TransportError`（含 `ConnectError`/各类 `Timeout`）重试；`HTTPStatusError`（4xx/5xx，已连上服务器）视为确定性错误不重试
- `fetch_dataset_urls`（下载页 30s）/ `download_and_parse`（zip 走默认 600s）统一走 `_get_with_retry`

### 3. config.py / .env.example —— 新增配置项

```bash
USDA_HTTP_PROXY=              # 极端情况下走代理根治，留空直连
USDA_DOWNLOAD_TIMEOUT=600     # 单次请求读/写超时
USDA_CONNECT_TIMEOUT=8        # TLS 握手超时，缩短以快速失败
USDA_DOWNLOAD_RETRIES=20      # 总尝试次数
USDA_DOWNLOAD_CONCURRENCY=5   # 每轮并发握手数
```

## 验证

完整 UA + 并发重试，端到端实测：

- `fetch_dataset_urls` ×3：**3/3 全过**（这是最初 8/8 全挂的点）。其中一次首轮并发被切、退避后第二轮蹭过——并发重试在「切断」发生时确实兜住底
- `download_and_parse foundation`：成功，解析 **363** 条（原始 395，过滤 32 条非 dict/null），3.2s
- 历史：`sr_legacy` 解析 **7793** 条亦验证过

## 备注

- 前端 `UsdaDataView.vue` 已有「上传 USDA zip」入口（`/usda/upload`）作为人工兜底：网络极差时浏览器手动下载再上传
- 差窗口下即便并发重试也可能连续失败，属正常网络波动；重试机制保证好窗口能蹭过，而非依赖单一请求成功率
- 未引入 `curl` 子进程或 `curl_cffi`：前者跨系统 TLS 后端不一致（Windows Schannel / Linux OpenSSL），后者在 Python 3.14 下 `OPENSSL_internal` 库错误 + 403，均不可靠
