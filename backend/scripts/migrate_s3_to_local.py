"""批量把 S3 上的所有图片文件下载到 backend/static/images/。

用法（在 backend/ 目录下）::

    python scripts/migrate_s3_to_local.py

依赖 backend/.env 中的 S3_* 配置（storage_backend=s3 非必需，脚本直读 S3_* 即可）。

幂等：本地已存在的文件自动跳过（不覆盖）。
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_BACKEND_DIR = _HERE.parent  # backend/
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.config import settings
from app.services.storage.s3 import S3Backend
from app.services.storage.effective import load_effective_storage_config

IMAGES_DIR = _BACKEND_DIR / "static" / "images"


def _migrate_all(
    backend: S3Backend,
    images_dir: Path,
    *,
    quiet: bool = False,
    progress_callback=None,
) -> tuple[int, int, int]:
    """核心迁移逻辑：list_objects_v2 分页 → get → 落本地。

    返回值: (uploaded, skipped, failed) 三元组。

    ``progress_callback``：可选回调函数，签名 ``(stage, current, total, message)``。
    """
    uploaded = 0
    skipped = 0
    failed = 0
    continuation = None
    all_keys = []

    # 分页列出所有 S3 对象
    while True:
        kwargs = {"Bucket": backend.bucket}
        if continuation:
            kwargs["ContinuationToken"] = continuation
        resp = backend.client.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []):
            all_keys.append(obj["Key"])
        if resp.get("IsTruncated") and resp.get("NextContinuationToken"):
            continuation = resp["NextContinuationToken"]
        else:
            break

    # 下载到本地
    for i, key in enumerate(all_keys):
        try:
            dest = images_dir / key
            if dest.exists():
                skipped += 1
                if not quiet:
                    print(f"  [跳过] {key} (本地已存在)")
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                data = backend.get(key)
                dest.write_bytes(data)
                uploaded += 1
                if not quiet:
                    print(f"  [下载] {key}")
        except Exception as e:
            failed += 1
            if not quiet:
                print(f"  [失败] {key}: {e}")

        if progress_callback:
            progress_callback("迁移到本地", i + 1, len(all_keys), key)

    return uploaded, skipped, failed


def main() -> int:
    """CLI 入口。"""
    if not IMAGES_DIR.is_dir():
        # 如果 images 目录不存在，创建它
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # ----- 配置校验 -----
    # 读取 effective S3 配置（不是向导填的临时配置）
    try:
        cfg = load_effective_storage_config()
    except Exception as e:
        print(f"[ERR] 加载有效 S3 配置失败: {e}")
        return 1

    if not cfg.s3_endpoint or not cfg.s3_bucket or not cfg.s3_access_key or not cfg.s3_secret_key:
        print(f"[ERR] 缺少 S3 有效配置（请先在后台配置 S3 并保存）")
        return 1

    # ----- 构造 S3Backend -----
    try:
        backend = S3Backend(
            endpoint=cfg.s3_endpoint,
            bucket=cfg.s3_bucket,
            access_key=cfg.s3_access_key,
            secret_key=cfg.s3_secret_key,
            region=cfg.s3_region,
            url_style=cfg.s3_url_style,
        )
    except Exception as e:
        print(f"[ERR] 创建 S3Backend 失败: {e}")
        return 1

    # ----- 执行迁移 -----
    print(f"[开始] 从 S3 下载图片到 {IMAGES_DIR}...\n")
    uploaded, skipped, failed = _migrate_all(backend, IMAGES_DIR)
    total = uploaded + skipped + failed
    print(
        f"\n[完成] 下载 {uploaded} / 跳过 {skipped} / 失败 {failed}"
        f" / 总计 {total}"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
