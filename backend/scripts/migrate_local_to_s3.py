"""批量把 backend/static/images/ 下所有图片文件上传到 S3 backend。

用法（在 backend/ 目录下）::

    python scripts/migrate_local_to_s3.py

依赖 backend/.env 中的 S3_* 配置（storage_backend=s3 非必需，脚本直读 S3_* 即可）。

幂等：已存在于 S3 上的文件自动跳过。
"""
from __future__ import annotations

import mimetypes
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_BACKEND_DIR = _HERE.parent  # backend/
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.config import settings
from app.services.storage.s3 import S3Backend
from app.services.storage.migrate import _migrate_to_s3_core

IMAGES_DIR = _BACKEND_DIR / "static" / "images"


def _infer_content_type(path: Path) -> str:
    """根据文件扩展名推断 MIME 类型。

    已知类型返标准 MIME，未知类型 fallback ``application/octet-stream``。
    """
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def _compute_key(file_path: Path, images_dir: Path | None = None) -> str:
    """计算上传到 S3 的 key。

    ``static/images/recipes/xxx.jpg`` → ``recipes/xxx.jpg``

    ``images_dir``：基准目录，默认为模块级 ``IMAGES_DIR``。
    始终使用 POSIX 风格路径分隔符，确保 Windows 下产出 ``recipes/xxx.jpg``
    而非 ``recipes\\xxx.jpg``。
    """
    base = images_dir or IMAGES_DIR
    rel = file_path.relative_to(base)
    return rel.as_posix()


def main() -> int:
    """CLI 入口。"""
    if not IMAGES_DIR.is_dir():
        print(f"[SKIP] 图片目录不存在: {IMAGES_DIR}")
        return 0

    # ----- 配置校验 -----
    missing = []
    if not settings.bootstrap_s3_endpoint:
        missing.append("BOOTSTRAP_S3_ENDPOINT")
    if not settings.bootstrap_s3_bucket:
        missing.append("BOOTSTRAP_S3_BUCKET")
    if not settings.bootstrap_s3_access_key:
        missing.append("BOOTSTRAP_S3_ACCESS_KEY")
    if not settings.bootstrap_s3_secret_key:
        missing.append("BOOTSTRAP_S3_SECRET_KEY")
    if missing:
        print(f"[ERR] 缺少 S3 配置（请检查 backend/.env）：{', '.join(missing)}")
        return 1

    # ----- 构造 S3Backend -----
    try:
        backend = S3Backend(
            endpoint=settings.bootstrap_s3_endpoint,
            bucket=settings.bootstrap_s3_bucket,
            access_key=settings.bootstrap_s3_access_key,
            secret_key=settings.bootstrap_s3_secret_key,
            region=settings.bootstrap_s3_region,
            url_style=settings.bootstrap_s3_url_style,
        )
    except Exception as e:
        print(f"[ERR] 创建 S3Backend 失败: {e}")
        return 1

    # ----- 执行迁移 -----
    print(f"[开始] 迁移图片到 S3...\n")
    uploaded, skipped, failed = _migrate_to_s3_core(backend, IMAGES_DIR)
    total = uploaded + skipped + failed
    if total == 0:
        print(f"[DONE] {IMAGES_DIR} 下没有文件，无需迁移")
    else:
        print(
            f"\n[完成] 上传 {uploaded} / 跳过 {skipped} / 失败 {failed}"
            f" / 总计 {total}"
        )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
