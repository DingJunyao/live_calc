# 外链图打包导出 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让云模式数据导出（full + mine）下载外链图并打包进 ZIP，管理员下原图（去 `?imageslim`）、普通用户下瘦身图。

**Architecture:** 在 `packaging.py` 新增并发下载辅助函数 `_download_remote_images`；改造 `_collect_image_files` 接收 `user`，扫描外链 → 下载 → 成功的改写 JSON 路径并打包、失败的保留外链并计数；`build_export_zip` 把 `user` 传入并用 `try/finally` 清理临时目录。

**Tech Stack:** Python / SQLAlchemy（后端导出服务）、`requests`（已有依赖）、`concurrent.futures.ThreadPoolExecutor`、pytest（mock `requests.get`）。

**Spec:** [2026-07-27-export-pack-remote-images-design.md](../specs/2026-07-27-export-pack-remote-images-design.md)

---

## File Structure

| 文件 | 责任 | 改动 |
|------|------|------|
| `backend/app/services/export/packaging.py` | 导出打包主编排 | 新增 `_download_remote_images`；改造 `_collect_image_files` 加 `user` 参数 + 路径改写 + 下载整合；`build_export_zip` 传 `user` + `try/finally` 清理临时目录 |
| `backend/tests/services/test_export_packaging.py` | 打包服务测试 | 新增 `_download_remote_images` 与 `_collect_image_files` 的单测（mock `requests.get`，纯 payload dict） |

无表结构变更，无 alembic/SQL。local 导入端、云库 DB 零改动。

---

## Task 1: 新增 `_download_remote_images` 辅助函数

**Files:**
- Modify: `backend/app/services/export/packaging.py`（顶部 import + 新增函数）
- Test: `backend/tests/services/test_export_packaging.py`（新增测试）

- [ ] **Step 1: 写失败测试**

在 `backend/tests/services/test_export_packaging.py` 末尾追加：

```python
from unittest.mock import patch, MagicMock
from app.services.export.packaging import _download_remote_images


def test_download_remote_images_success_and_paths():
    """成功下载：返回 {url: (rel, tmp_path)}，rel 为 images/<basename>。"""
    urls = ["https://cdn.example.com/livecalc/abc.jpg?imageslim"]
    with patch("app.services.export.packaging.requests.get") as mock_get:
        mock_get.return_value = MagicMock(content=b"\x89PNG fake", raise_for_status=lambda: None)
        downloaded, failed, tmpdir = _download_remote_images(urls, is_admin=False)
    assert failed == 0
    assert len(downloaded) == 1
    rel, tmp_path = downloaded[urls[0]]
    assert rel == "images/abc.jpg"
    import os
    assert os.path.exists(tmp_path)


def test_download_remote_images_admin_strips_query():
    """管理员：下载 URL 去 query（下原图）。"""
    urls = ["https://cdn.example.com/x/keep.png?imageslim"]
    with patch("app.services.export.packaging.requests.get") as mock_get:
        mock_get.return_value = MagicMock(content=b"img", raise_for_status=lambda: None)
        _download_remote_images(urls, is_admin=True)
    # 捕获实际请求的 URL
    called_url = mock_get.call_args[0][0]
    assert called_url == "https://cdn.example.com/x/keep.png"
    assert "?imageslim" not in called_url


def test_download_remote_images_non_admin_keeps_query():
    """普通用户：URL 原样（含瘦身 query）。"""
    urls = ["https://cdn.example.com/x/keep.png?imageslim"]
    with patch("app.services.export.packaging.requests.get") as mock_get:
        mock_get.return_value = MagicMock(content=b"img", raise_for_status=lambda: None)
        _download_remote_images(urls, is_admin=False)
    called_url = mock_get.call_args[0][0]
    assert called_url == "https://cdn.example.com/x/keep.png?imageslim"


def test_download_remote_images_failure_counted():
    """下载失败：计入 failed，不抛异常。"""
    urls = ["https://cdn.example.com/a.jpg", "https://cdn.example.com/b.jpg"]
    def fake_get(url, timeout=None):
        if "b.jpg" in url:
            raise Exception("network error")
        return MagicMock(content=b"ok", raise_for_status=lambda: None)
    with patch("app.services.export.packaging.requests.get", side_effect=fake_get):
        downloaded, failed, tmpdir = _download_remote_images(urls, is_admin=True)
    assert failed == 1
    assert len(downloaded) == 1  # a.jpg 成功


def test_download_remote_images_dedup_basenames():
    """同名 basename 去重：第二个加 _2。"""
    urls = ["https://cdn.example.com/dup.jpg", "https://cdn.example.com/other/dup.jpg"]
    with patch("app.services.export.packaging.requests.get") as mock_get:
        mock_get.return_value = MagicMock(content=b"x", raise_for_status=lambda: None)
        downloaded, failed, tmpdir = _download_remote_images(urls, is_admin=True)
    rels = {v[0] for v in downloaded.values()}
    assert "images/dup.jpg" in rels
    assert "images/dup_2.jpg" in rels
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/services/test_export_packaging.py -v -k download_remote`
Expected: FAIL（`ImportError: cannot import name '_download_remote_images'`）

- [ ] **Step 3: 实现 `_download_remote_images`**

在 `backend/app/services/export/packaging.py` 顶部 import 区补充（`tempfile`、`requests`、`ThreadPoolExecutor`；`Path`/`_UNSAFE_FILENAME` 已有）：

```python
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor

import requests
```

在 `_collect_image_files` 函数**之前**插入：

```python
def _download_remote_images(image_urls: list, is_admin: bool,
                            max_workers: int = 8, timeout: int = 30):
    """并发下载外链图到临时目录。

    - is_admin=True：去掉 URL query（下原图）；否则原样（瘦身图）。
    返回 (downloaded, failed, tmpdir_path)：
      downloaded: {原 url: (zip 内相对路径, 临时文件绝对路径)}
      failed: 下载失败数
      tmpdir_path: 临时目录（调用方负责清理）
    """
    tmpdir = tempfile.mkdtemp(prefix="export_img_")

    def fetch(url):
        fetch_url = url.split("?", 1)[0] if is_admin else url
        try:
            resp = requests.get(fetch_url, timeout=timeout)
            resp.raise_for_status()
        except Exception:
            return None
        base = fetch_url.rsplit("/", 1)[-1] or "image"
        base = _UNSAFE_FILENAME.sub("_", base).strip() or "image"
        return url, base, resp.content

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        results = list(ex.map(fetch, image_urls))

    downloaded = {}
    used_rels = set()
    failed = 0
    for r in results:
        if r is None:
            failed += 1
            continue
        url, base, content = r
        rel = "images/" + base
        n = 2
        while rel in used_rels:
            rel = f"images/{base}_{n}"
            n += 1
        used_rels.add(rel)
        tmp_path = Path(tmpdir) / base
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_bytes(content)
        downloaded[url] = (rel, str(tmp_path))

    return downloaded, failed, tmpdir
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/services/test_export_packaging.py -v -k download_remote`
Expected: 5 passed

- [ ] **Step 5: 语法检查**

Run: `cd backend && ../.venv/Scripts/python.exe -m py_compile app/services/export/packaging.py`
Expected: 无输出（成功）

---

## Task 2: 改造 `_collect_image_files` 整合下载与路径改写

**Files:**
- Modify: `backend/app/services/export/packaging.py:59-93`（`_collect_image_files`）
- Test: `backend/tests/services/test_export_packaging.py`

- [ ] **Step 1: 写失败测试**

在 `test_export_packaging.py` 追加：

```python
from app.services.export.packaging import _collect_image_files


def _fake_user(admin: bool):
    u = MagicMock()
    u.is_admin = admin
    return u


def test_collect_image_files_rewrites_remote_and_packs(monkeypatch):
    """外链图下载成功：JSON 改写为相对路径，图文件收集打包。"""
    recipes = [{"images": ["https://cdn.example.com/r1/foo.jpg?imageslim"]}]
    products = [{"image_url": "https://cdn.example.com/p1/bar.png"}]
    monkeypatch.setattr(
        "app.services.export.packaging._download_remote_images",
        lambda urls, is_admin: (
            {
                "https://cdn.example.com/r1/foo.jpg?imageslim": ("images/foo.jpg", "/tmp/_/foo.jpg"),
                "https://cdn.example.com/p1/bar.png": ("images/bar.png", "/tmp/_/bar.png"),
            },
            0,
            "/tmp/_dummy",
        ),
    )
    manifest = {}
    files, tmpdir = _collect_image_files(manifest, recipes, products, user=_fake_user(admin=False))
    # JSON 被改写
    assert recipes[0]["images"] == ["images/foo.jpg"]
    assert products[0]["image_url"] == "images/bar.png"
    # 图文件收集
    rels = [f[0] for f in files]
    assert "images/foo.jpg" in rels
    assert "images/bar.png" in rels
    # manifest 统计
    assert manifest["image_summary"]["downloaded"] == 2
    assert manifest["image_summary"]["failed"] == 0


def test_collect_image_files_failed_keeps_remote(monkeypatch):
    """下载失败：JSON 保留外链 URL，计入 failed，不打包该图。"""
    recipes = [{"images": ["https://cdn.example.com/missing.jpg"]}]
    monkeypatch.setattr(
        "app.services.export.packaging._download_remote_images",
        lambda urls, is_admin: ({}, 1, "/tmp/_dummy"),
    )
    manifest = {}
    files, tmpdir = _collect_image_files(manifest, recipes, [], user=_fake_user(admin=True))
    assert recipes[0]["images"] == ["https://cdn.example.com/missing.jpg"]  # 保留外链
    assert manifest["image_summary"]["failed"] == 1
    assert manifest["image_summary"]["downloaded"] == 0
    assert all("missing.jpg" not in f[0] for f in files)


def test_collect_image_files_admin_flag_passed(monkeypatch):
    """user.is_admin 透传给 _download_remote_images。"""
    captured = {}
    def fake_dl(urls, is_admin):
        captured["is_admin"] = is_admin
        return {}, 0, "/tmp/_dummy"
    monkeypatch.setattr("app.services.export.packaging._download_remote_images", fake_dl)
    _collect_image_files({}, [{"images": ["https://x/y.jpg"]}], [], user=_fake_user(admin=True))
    assert captured["is_admin"] is True
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/services/test_export_packaging.py -v -k collect_image`
Expected: FAIL（旧 `_collect_image_files` 签名不接 `user`，且不改写外链）

- [ ] **Step 3: 改造 `_collect_image_files`**

用下面整段替换 `backend/app/services/export/packaging.py` 中现有的 `_collect_image_files`（从 `def _collect_image_files` 到其 `return files` 结束）：

```python
def _collect_image_files(manifest: dict, recipes_payload: list, products_payload: list,
                         user=None) -> tuple:
    """扫描图片，返回 (files, tmpdir_to_clean)。

    - 外链图：下载到临时目录；成功的把 JSON 里 URL 改写为 images/<basename> 相对路径并打包；
      失败的保留外链 URL（不打包），计入 failed。
    - 本地图（STATIC_DIR/images/...）：存在则打包，缺失计入 skipped_local_missing。
    - 管理员（user.is_admin）下载时去 query 下原图，由 _download_remote_images 处理。
    """
    files = []
    seen = set()
    skipped_local_missing = 0

    # 1) 收集去重的外链 URL
    remote_urls: list = []
    seen_urls: set = set()

    def _is_remote(rel):
        return rel and (rel.startswith("http://") or rel.startswith("https://"))

    for r in recipes_payload:
        for img in r.get("images", []):
            if _is_remote(img) and img not in seen_urls:
                seen_urls.add(img)
                remote_urls.append(img)
    for p in products_payload:
        url = p.get("image_url")
        if _is_remote(url) and url not in seen_urls:
            seen_urls.add(url)
            remote_urls.append(url)

    # 2) 下载外链
    is_admin = bool(getattr(user, "is_admin", False))
    downloaded, dl_failed, tmpdir = _download_remote_images(remote_urls, is_admin)

    # 3) 遍历 payload：改写外链 + 收集打包
    def _handle(rel, payload_obj, key, idx=None):
        nonlocal skipped_local_missing
        if not rel:
            return
        if _is_remote(rel):
            if rel not in downloaded:
                return  # 失败：保留外链，不打包
            pack_rel, phys = downloaded[rel]
            if idx is not None:
                payload_obj[key][idx] = pack_rel
            else:
                payload_obj[key] = pack_rel
        else:
            phys = STATIC_DIR / rel
            if not phys.exists():
                skipped_local_missing += 1
                return
            pack_rel = rel
        if pack_rel in seen:
            return
        seen.add(pack_rel)
        files.append((pack_rel, str(phys)))

    for r in recipes_payload:
        for i, img in enumerate(r.get("images", [])):
            _handle(img, r, "images", i)
    for p in products_payload:
        _handle(p.get("image_url"), p, "image_url")

    # 4) manifest 统计
    summary = manifest.setdefault("image_summary", {})
    summary["downloaded"] = len(downloaded)
    summary["failed"] = dl_failed
    summary["skipped_local_missing"] = skipped_local_missing
    summary["skipped_remote"] = dl_failed  # 向后兼容旧字段
    if downloaded or dl_failed:
        manifest.setdefault("notes", []).append(
            f"{len(downloaded)} 个外链图已下载打包，{dl_failed} 个下载失败保留外链"
        )

    return files, tmpdir
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/services/test_export_packaging.py -v -k collect_image`
Expected: 3 passed

- [ ] **Step 5: 语法检查**

Run: `cd backend && ../.venv/Scripts/python.exe -m py_compile app/services/export/packaging.py`
Expected: 无输出

---

## Task 3: `build_export_zip` 传 user + 临时目录清理

**Files:**
- Modify: `backend/app/services/export/packaging.py`（`build_export_zip` 的图片收集调用 + zip 写入 + 清理）

- [ ] **Step 1: 改造 `build_export_zip`**

定位 `build_export_zip` 中现有的两处：

(a) 图片收集调用（约 line 430，原为 `image_files = _collect_image_files(manifest, recipes_payload, products_payload)`），改为：

```python
    # ---- 图片收集（外链图下载打包；image_summary 由 _collect_image_files 统一维护）----
    image_files, img_tmpdir = _collect_image_files(manifest, recipes_payload, products_payload, user)
```

(b) zip 写入段（约 line 432-457，`buf = io.BytesIO()` 起、到 `return buf.getvalue(), manifest` 止），用 `try/finally` 包裹并在末尾清理临时目录。把整段改成：

```python
    # ---- 写 zip ----
    buf = io.BytesIO()
    try:
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            zf.writestr("ingredients.json", json.dumps(ingredients_payload, ensure_ascii=False, indent=2))
            zf.writestr("nutritions.json", json.dumps(nutritions_payload, ensure_ascii=False, indent=2))
            zf.writestr("units.json", json.dumps(units_payload, ensure_ascii=False, indent=2))
            zf.writestr("unit_conversions.json", json.dumps(conversions_payload, ensure_ascii=False, indent=2))
            zf.writestr("ingredient_categories.json", json.dumps(categories_payload, ensure_ascii=False, indent=2))
            zf.writestr("ingredient_hierarchy.json", json.dumps(hierarchy_payload, ensure_ascii=False, indent=2))
            zf.writestr("entity_densities.json", json.dumps(densities_payload, ensure_ascii=False, indent=2))
            zf.writestr("entity_unit_overrides.json", json.dumps(unit_overrides_payload, ensure_ascii=False, indent=2))
            zf.writestr("products.json", json.dumps(products_payload, ensure_ascii=False, indent=2))
            zf.writestr("product_barcodes.json", json.dumps(barcodes_payload, ensure_ascii=False, indent=2))
            zf.writestr("product_ingredient_links.json", json.dumps(links_payload, ensure_ascii=False, indent=2))
            zf.writestr("price_records.json", json.dumps(records_payload, ensure_ascii=False, indent=2))
            zf.writestr("merchants.json", json.dumps(merchants_payload, ensure_ascii=False, indent=2))
            zf.writestr("user_places.json", json.dumps(places_payload, ensure_ascii=False, indent=2))
            zf.writestr("blacklist_groups.json", json.dumps(bl_groups_payload, ensure_ascii=False, indent=2))
            zf.writestr("user_ingredient_blacklist.json", json.dumps(bl_entries_payload, ensure_ascii=False, indent=2))
            zf.writestr("blacklist_group_subscriptions.json", json.dumps(bl_subs_payload, ensure_ascii=False, indent=2))
            for fname, payload in recipe_file_index:
                zf.writestr(fname, json.dumps(payload, ensure_ascii=False, indent=2))
            for rel, phys in image_files:
                zf.write(phys, rel)
        return buf.getvalue(), manifest
    finally:
        if img_tmpdir:
            shutil.rmtree(img_tmpdir, ignore_errors=True)
```

> 注意：上面 `zf.writestr(...)` 各行须与现有文件**完全一致**（文件名、payload 变量名、顺序）。实施时先读现有 build_export_zip 的 zip 写入段，逐行对照替换，切勿漏写或改序。`shutil` 已在 Task 1 顶部 import。

- [ ] **Step 2: 语法检查**

Run: `cd backend && ../.venv/Scripts/python.exe -m py_compile app/services/export/packaging.py`
Expected: 无输出

- [ ] **Step 3: 全量回归测试**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/services/test_export_packaging.py tests/services/test_export_reachability.py tests/test_export.py -v`
Expected: 全 passed（既有测试 + Task1/2 新增测试）。既有 `test_export_data_full/mine` 仍通过（真实库 + 真实外链下载，若网络不通则外链计入 failed，不影响断言）。

- [ ] **Step 4: 端到端手动验证（真实库 + 管理员原图）**

Run（一次性脚本，验证 ZIP 含 images/、manifest 统计、管理员去 query）：

```bash
cd backend && ../.venv/Scripts/python.exe <<'EOF'
import sys; sys.path.insert(0,'.')
from app.core.database import SessionLocal
from app.models.user import User
from app.services.export.packaging import build_export_zip
import io, zipfile, json
db = SessionLocal()
u = db.query(User).filter(User.is_admin == True).first() or db.query(User).first()
zb, m = build_export_zip(db, u, 'full')
zf = zipfile.ZipFile(io.BytesIO(zb))
imgs = [n for n in zf.namelist() if n.startswith('images/')]
print('user_is_admin:', u.is_admin)
print('image_summary:', m.get('image_summary'))
print('packed image files:', len(imgs), imgs[:5])
print('notes:', m.get('notes'))
EOF
```
Expected: `image_summary.downloaded > 0`（真实库有外链图时）；`packed image files > 0`；管理员时下载的为原图（验证：抽查 manifest.notes + image_summary.downloaded 数与外链数接近）。

---

## Self-Review

**Spec coverage：**
- full + mine 都打包 → Task 3 端到端（build_export_zip 对两 scope 都生效，_collect_image_files 不区分 scope） ✓
- 管理员去 query 下原图 / 普通用户瘦身 → Task 1 `test_download_remote_images_admin/non_admin` ✓
- 成功改写相对路径 + 打包 → Task 2 `test_collect_image_files_rewrites_remote_and_packs` ✓
- 失败保留外链 + 计 failed + 不阻断 → Task 1 `test_download_remote_images_failure_counted` + Task 2 `test_collect_image_files_failed_keeps_remote` ✓
- 本地图照旧 → Task 2 `_handle` 本地分支保留 ✓
- manifest downloaded/failed 统计 → Task 2 ✓
- local 导入端零改动 → 设计已论证，无任务需要（spec 4.7） ✓
- 临时目录清理 → Task 3 try/finally + Step 3 回归 ✓

**Placeholder scan：** 无 TBD/TODO；Task 3 Step 1 的 writestr 清单注明「与现有逐行对照」，属实施约束非占位。代码块完整。

**Type consistency：** `_download_remote_images` 返回 `(dict, int, str)`；`_collect_image_files` 返回 `(files, tmpdir)`，`build_export_zip` 解包 `image_files, img_tmpdir`——一致。`_handle_img`/`_handle`、`is_admin`、`downloaded`/`used_rels` 命名前后一致。

无 git commit 步骤（遵循项目「未主动要求不提交」规矩）。
