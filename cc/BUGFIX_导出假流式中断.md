# 数据导出 full 200 但 net::ERR_FAILED（XHR blob 累积失败，fetch 流式读修复）

## 现象
- 个人中心「数据导出」全量（full）失败，后端**无报错**
- DevTools：`GET .../export/data?scope=full` 状态 **200**，但「无法加载响应数据：No data found」
- 前端：`AxiosError: Network Error`、`net::ERR_FAILED 200 (OK)`
- mine（仅本人）模式不报错（体积小）

## 根因（真正主因）
**浏览器 XHR `responseType:'blob'` 在内部累积 ~100MB 响应成 blob 时失败**（`onerror` / `Failed to fetch`），无论经 Vite proxy 还是直连后端都失败。axios 用的就是 XHR，所以 axios blob 下载必失败。

附带叠加：Vite dev proxy 对带 Accept-Encoding 的大响应流式 chunked 透传会吞字节（dev 经 proxy 时进一步损坏）。

## 调试（5 轮，前 3 轮全栽在「curl 不是浏览器」）

### 第 1-2 轮：假流式 → Response → 真分块（curl 测完整，用户失败）
curl 直连后端 / 经 proxy 都测「完整」。**用户浏览器仍失败**。
盲点：①curl 默认不带 `Accept-Encoding`，测的是和浏览器不同的代码路径；②curl 没有 XHR/blob 引擎，永远测不出浏览器 blob 累积失败。

### 第 3 轮：dev 绕过 proxy（curl 测完整，用户浏览器仍失败）
发现 curl vs 浏览器 Accept-Encoding 差异 + proxy 吞字节，改前端 dev 直连后端 + CORS `expose_headers`。curl 跨域直连完整。**用户浏览器仍失败**（URL 已变 8000，绕过 proxy 生效，但仍 ERR_FAILED）——证明 proxy 不是唯一元凶，浏览器侧另有问题。

### 第 4 轮（关键突破）：edge-devtools 浏览器视角测试
curl 已到极限，换 edge-devtools 直接测浏览器：
| 方式 | 结果 |
|---|---|
| `fetch + getReader` 流式读 | ✅ 成功（received 104800319, err null, 2.5s） |
| `XHR + responseType:'blob'`（axios 用） | ❌ 失败（error, status 0, 14.5s）—— 复现用户问题 |
| `fetch + response.blob()` | ❌ 失败（Failed to fetch） |
| `fetch + getReader + 手动 new Blob(chunks)` | ✅ 成功（blobSize 104800319） |

**定位**：浏览器内部累积 ~100MB blob 的路径（XHR blob / response.blob()）失败；fetch 流式读（JS 主动消费 chunks）+ 手动 `new Blob` 成功。

## 最终修复
1. **前端 [ProfileView doExport](frontend/src/views/profile/ProfileView.vue)**：
   - 弃 axios（XHR blob），改 `fetch` + `resp.body.getReader()` 流式读 chunks + 手动 `new Blob(chunks, {type:'application/zip'})` + `createObjectURL` + `<a download>`
   - dev 绕过 Vite proxy 直连后端（`directHost = import.meta.env.DEV ? VITE_DEV_BACKEND_URL||'http://localhost:8000' : ''`，避 proxy 吞字节），prod 同源走 Nginx
   - 删 axios import（不再用）+ 过时注释
2. **后端 [main.py CORS](backend/app/main.py)**：`expose_headers=["Content-Disposition"]`（跨域读文件名）
3. **export.py 真分块保留**（dev 直连 / prod Nginx 都正确转发 chunked）

## 验证
- edge-devtools 浏览器视角：`fetch + getReader + new Blob` 成功，blobSize 104800319
- 前端 build 38.23s 通过（precache 128 entries）
- 待用户浏览器实测最终确认

## 教训
1. **curl 测不出浏览器 XHR/blob 的累积失败**——curl 不是浏览器，没 XHR/blob 引擎。浏览器侧问题必须用浏览器 DevTools（edge-devtools MCP）测，别在 curl 上打转
2. **curl 测代理层大响应必须带浏览器同款 `Accept-Encoding`**，否则测不同代码路径（curl 走聚合、浏览器走流式）
3. **大文件下载避免 axios/XHR `responseType:'blob'`**（浏览器内部累积大 blob 不稳），用 fetch 流式读 + 手动 new Blob；更彻底可用 `<a download>` 原生下载（流式写盘，0 JS 内存，但需后端支持 query token 等无 header 鉴权）
4. systematic-debugging：curl 验证后端/代理层 OK 但浏览器仍失败时，立即转浏览器 DevTools 测浏览器视角
5. 多轮修复失败（3+）要质疑假设层次——前几轮全在「响应内容/编码/proxy」打转，真正根因在「浏览器 blob 累积」，差了一个抽象层；每轮的 curl 假阳性（curl 完整）都在误导
