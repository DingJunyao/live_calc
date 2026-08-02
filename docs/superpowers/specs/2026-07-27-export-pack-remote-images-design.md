# 外链图打包导出 设计文档

> 日期：2026-07-27
> 模块：`backend/app/services/export/packaging.py`

## 一、背景

云模式数据导出 `build_export_zip` 当前对图片只打包本地 `STATIC_DIR` 内的相对路径图，外链 `http(s)://` 图（OSS CDN，`static.a4ding.com`）一律跳过——见 [_collect_image_files._handle](../../../backend/app/services/export/packaging.py)：`if rel.startswith("http://") or rel.startswith("https://"): skipped += 1; return`。

后果：全量导出的 ZIP 不含图片，manifest `image_summary.skipped_remote` 记录被跳过的外链数（实测 341 张）。用户要求：既然是全量导出，外链图也应当打包。

## 二、范围

- **full 和 mine 两种 scope 都下载外链图并打包**（用户拍板）。
- 改动集中在后端 `packaging.build_export_zip`。
- **local 导入端现成兼容**（[exportImport.ts:396-429](../../../frontend/src/api/local/handlers/exportImport.ts#L396) 已支持「相对路径图从 ZIP 解包」、外链才跳过），前端零改动。
- **云库 DB 不动**：只改导出 ZIP 内容，云端 `getImageUrl` 无影响。

## 三、方案选定

**方案 A：临时目录并发下载**（采纳）。

扫描所有外链 URL → 并发下载到临时目录 → 成功的改写 JSON 路径并打包、失败的保留外链 URL 并记录 → `try/finally` 清理临时目录。

弃用方案 B（流式直写 ZIP）：`zipfile.writestr` 要求内容 bytes（下载完才知成败），且需先确定 JSON 路径映射，实际仍要先落盘再写，复杂度高于 A、收益小。

## 四、详细设计

### 4.1 下载

- 扫描 `recipes_payload[].images` + `products_payload[].image_url` 中的外链 URL（`http://` / `https://` 开头）。
- 并发下载：`ThreadPoolExecutor(max_workers=8)`，单图超时 30s。
- 用项目已有依赖 `requests`（同步，契合 `build_export_zip` 同步签名）。
- 临时目录 `tempfile.mkdtemp(prefix="export_img_")`，`try/finally` 清理。

### 4.2 管理员原图策略（用户要求）

下载时按 `user.is_admin` 区分：

- **管理员导出**：去掉 URL query string（`?imageslim` 等），下**原图**（备份用途，要最高质量）。
- **普通用户导出**：原样 URL 下载（含 `?imageslim`，拿瘦身图，体积小）。

去 query：`url.split("?", 1)[0]`。

### 4.3 路径改写（成功的图）

- `basename` = URL 的 path 末段去 query，经 `_UNSAFE_FILENAME` 清洗（复用既有正则）。
- `rel` = `"images/" + basename`；与已收集路径重名时追加 `_2` / `_3` 去重。
- JSON 里该外链 URL 改写为 `rel`（写入 `recipes_payload` 的 `images[]`、`products_payload` 的 `image_url`）。
- 图文件以 `rel` 路径打包进 ZIP。

### 4.4 失败处理

- 下载失败（网络 / 4xx / 5xx / 超时）的图：**JSON 保留原外链 URL**（导入端仍可在线访问），不打包文件，计入 `failed`。
- **不阻断导出**——单图失败不影响其余。

### 4.5 本地图与 storage key 图（主要场景）

实测当前云库 `Recipe.images` 存的是 **storage key**（如 `recipes/上汤娃娃菜_0.png`），不是 http 外链——图物理在 S3，DB 只存 key。这是用户数据的主要形态，必须覆盖。

- **本地图**（`STATIC_DIR/images/...` 存在）：照旧打包。
- **storage key 图**（`recipes/xxx`、`/static/images/xxx`、`avatars/xxx` 等，STATIC_DIR 查不到）：用 `storage.get(key)` 直接读 S3 bytes → 写临时文件 → 打包到**原 key 路径**（JSON 不改写，key 本就是相对路径，导入端按原 key 解包）。
  - `storage.get` 抛 `FileNotFoundError`（key 不在 S3）→ 计 `failed`，不阻断。
  - 走 S3 SDK 直读（[s3.py:98](../../../backend/app/services/storage/s3.py#L98) `get_object`），**不经 CDN**——无 UA 拦截、天然原图（`?imageslim` 只是 CDN 实时处理，S3 存的是原图，故 admin/普通用户一致，无需去 query）。
- http 外链图（少数）：走 4.1 的 `requests` 下载（admin 去 query 下原图）。

### 4.5b 三类图的分发逻辑（`_collect_image_files._handle`）

| 图来源 | 判定 | 处理 |
|--------|------|------|
| http(s) 外链 | `startswith("http")` | `_download_remote_images` 下载 → 改写 JSON 为 `images/<basename>` |
| 本地图存在 | STATIC_DIR/rel 存在 | 直接打包 |
| storage key（本地缺失） | STATIC_DIR/rel 不存在 | `storage.get(key)` 读 S3 → 打包到原 key，JSON 不改写 |

### 4.6 manifest 统计

`image_summary` 扩展为：

```json
{
  "downloaded": <成功下载数>,
  "failed": <失败数>,
  "skipped_local_missing": <本地缺失数>,
  "skipped_remote": <兼容保留，失败也算入>
}
```

`notes` 文案更新为：「N 个外链图已下载打包，M 个下载失败保留外链」。

### 4.7 local 导入端兼容

`frontend/src/api/local/handlers/exportImport.ts` 的图片解包逻辑（line 396-429）：按 `images/xxx` 相对路径匹配 ZIP 内文件、解包存 IndexedDB；仅 `http(s)://` 开头的外链才 `continue` 跳过。

路径改写后 JSON 是相对路径 → local 导入自动解包 → **前端零改动**。

## 五、涉及文件

| 文件 | 改动 |
|------|------|
| `backend/app/services/export/packaging.py` | `_collect_image_files` 改造：接收 `user`，扫描外链 → 下载 → 改写路径 → 收集打包；`build_export_zip` 把 `user` 传入 |

无表结构变更，无 alembic/SQL。

## 六、验收标准

1. full 导出：外链图下载打包，`recipe.images` / `product.image_url` 改写为相对路径；该 ZIP 在 local 模式导入后，菜谱/商品图片正常显示。
2. mine 导出：同上。
3. 管理员导出：打包的图为原图（URL 去 `?imageslim`）。
4. 普通用户导出：打包的图为瘦身图（URL 含 `?imageslim`）。
5. 下载失败：JSON 保留外链 URL，manifest 记 `failed`，导出继续不阻断。
6. 临时目录在导出结束后清理（含异常路径）。
7. 既有本地 `STATIC_DIR` 图片打包逻辑不受影响。
8. manifest `image_summary` 含 `downloaded` / `failed` 统计。
