# 外链图打包导出（功能实现）

## 背景
云模式全量导出对 OSS CDN 外链图（`http(s)://`）一律跳过（[_collect_image_files._handle:72](../backend/app/services/export/packaging.py) 跳 http），致 ZIP 不含图（实测 341 张外链全跳）。用户要求：全量导出当打包外链图，且管理员下原图、普通用户下瘦身图。

## 方案（3 task，subagent-driven + TDD）
1. **`_download_remote_images(image_urls, is_admin)`**（[packaging.py:63](../backend/app/services/export/packaging.py#L63)）：`ThreadPoolExecutor` 并发下载（8 并发/30s 超时）；`is_admin` 去 `?imageslim` query 下原图、否则原样瘦身图；basename 用 `_UNSAFE_FILENAME` 清洗、同名 `name_2.ext` 去重；失败计入 `failed` 不抛异常；返回 `(downloaded:{url:(rel,tmp_path)}, failed, tmpdir)`。
2. **`_collect_image_files` 改造**（[packaging.py:117](../backend/app/services/export/packaging.py#L117)）：签名加 `user`、返回 `(files, tmpdir)`。收集去重外链 URL → 调 `_download_remote_images`（透传 `is_admin`）→ 成功的把 JSON 里 URL 改写为 `images/<basename>` 相对路径并打包（recipe.images 用 idx 改 list、product.image_url 直赋）、失败的保留外链 URL 不打包计 `failed`、本地图（STATIC_DIR）照旧；manifest `image_summary` 含 `downloaded/failed/skipped_local_missing/skipped_remote`(兼容)。
3. **`build_export_zip` 整合**（[packaging.py:530/534/560](../backend/app/services/export/packaging.py#L530)）：`_collect_image_files` 传 `user`、解包 `(image_files, img_tmpdir)`；zip 写入段 `try/finally` 包裹，`finally` 用 `shutil.rmtree(img_tmpdir, ignore_errors=True)` 清理临时目录；19 条 `zf.writestr` 逐行保留。

## 关键文件
- 改：`backend/app/services/export/packaging.py`
- 测：`backend/tests/services/test_export_packaging.py`（8 新单测：5 download + 3 collect，mock `requests.get`）

无表结构变更，无 alembic/SQL。local 导入端 [exportImport.ts:396](../frontend/src/api/local/handlers/exportImport.ts#L396) 现成兼容（相对路径图从 ZIP 解包），前端零改动。云库 DB 不动。

## 验证
- 8 单测（mock requests，覆盖成功/admin 去 query/非 admin 保留 query/失败计数/basename 去重 + 改写/失败保留/admin 透传）+ 既有回归（真实库 test_export_data_full/mine 等）**16 passed**，`py_compile` 干净。
- 端到端脚本（真实 sqlite 库 + admin）：当前 `backend/data/livecalc.db` 的 Recipe.images 是相对路径（`images/xxx`）且 STATIC_DIR 文件缺失 → `skipped_local_missing=342`、`downloaded=0`——**未触发真实外链下载**。即：当前 sqlite 库无外链图，要在「有外链图的库」（如 22:00 那个 PG/MySQL，Recipe.images 存 `https://static.a4ding.com/...`）导出才会真实下载打包外链图。代码已就绪，单测 mock 覆盖了下载/改写/失败逻辑。

## Task 4 扩展：storage key 图（DB 主要形态，关键）

用户反馈「图都在 S3 但导出还是没图」→ 复查发现：云库 `Recipe.images` 存的是 **storage key**（`recipes/上汤娃娃菜_0.png` 这种相对 key），**不是 http 外链**。图物理在 S3，运行时后端 `/api/v1/images/<key>` 端点用 storage service 读。Task 1-3 的 http 外链下载对这些 key 不触发（走 STATIC_DIR 查不到 → skipped_local_missing）。

**方案**：`_collect_image_files._handle` 加第三分支——本地图 STATIC_DIR 缺失时，`storage.get(key)` 直读 S3 bytes（[s3.py:98](../backend/app/services/storage/s3.py#L98) `get_object`，不经 CDN）→ 写临时目录 → 打包到 **`images/<key>`**（与本地图片模式一致，避免与 `recipes/*.json` 混杂），JSON 改写为 `images/<key>`。`storage.get` 抛异常（FileNotFoundError 等）→ 计 `s3_missing`、JSON 保留原 key。顶部 `from app.services.storage.factory import get_storage`，`_collect` 预加载 `storage = get_storage()`（失败则 None，跳过 S3 读）。

**路径策略修正**：初版打包到原 key（`recipes/xxx`）致 `recipes/` 下图片与菜谱 json 混杂；改为统一归 `images/<key>`（`recipes/foo.png` → `images/recipes/foo.png`），JSON 改写，与本地图（`images/...`）一致。

**优于 http 下载**：S3 SDK 直读原图，无 UA 拦截（对比 [BUGFIX_USDA_DOWNLOAD_SSL_RETRY](BUGFIX_USDA_DOWNLOAD_SSL_RETRY.md) 的 WAF 拦 `python-requests`）、天然原图（`?imageslim` 只是 CDN 实时处理、S3 存的是原图，故 admin/普通用户一致，无需去 query）。

**全量端到端实测**：当前 sqlite 库 **340 张 S3 图读取打包**（`s3_downloaded=340`，去重后 `images/` 339 条）、2 张 S3 缺失（`s3_missing=2`，历史遗留图），zip 99.9MB（含图，原 33MB），耗时 46s，**`recipes/` 下 0 图片（纯菜谱 json，不混杂）**。**用户「图都在 S3 导出没图」+「图片和 json 混杂」问题解决。**

单测增 2 个（storage 成功读/缺失）共 10 个 + 既有回归 passed。manifest `image_summary` 增 `s3_downloaded/s3_missing`。

## 教训
- 既有 `zf.writestr` 清单须逐行读现有对照（计划参考变量名可能笔误，如本例 `ingredients_doc` 实际 ≠ 计划写的 `ingredients_payload`）——回归测试是兜底（NameError 会崩）。
- 跨库数据状态差异（sqlite 库图相对路径 vs 另一库图外链）会掩盖特性效果，端到端验证要选对库。
- subagent-driven 逐 task 派单 + controller 读码审查（spec+质量两阶段），3 task 干净落地、边界守住（每 task 不越界改他 task 的函数）。

## 文档
- spec：[docs/superpowers/specs/2026-07-27-export-pack-remote-images-design.md](../docs/superpowers/specs/2026-07-27-export-pack-remote-images-design.md)
- plan：[docs/superpowers/plans/2026-07-27-export-pack-remote-images.md](../docs/superpowers/plans/2026-07-27-export-pack-remote-images.md)

未 commit（项目规矩「未主动要求不提交」）。后续：用户在「有外链图的库」实测导出验证真实下载打包效果；按需提交。
