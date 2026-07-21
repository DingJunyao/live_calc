"""图片存储配置管理 API（管理员）。spec §4.5。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.user import User
from app.models.storage_configuration import StorageConfiguration
from app.services.storage.effective import load_effective_storage_config
from app.services.storage.factory import reset_storage

router = APIRouter(prefix="/admin/storage-config", tags=["图片存储配置"])


class StorageConfigUpdate(BaseModel):
    backend: Optional[str] = None
    storage_base_url: Optional[str] = None
    s3_endpoint: Optional[str] = None
    s3_access_key: Optional[str] = None      # null/None = 不变
    s3_secret_key: Optional[str] = None      # null/None = 不变
    s3_bucket: Optional[str] = None
    s3_region: Optional[str] = None
    s3_url_style: Optional[str] = None
    s3_base_path: Optional[str] = None
    s3_custom_domain: Optional[str] = None
    s3_url_suffix: Optional[str] = None


class StorageConfigTest(BaseModel):
    backend: str
    s3_endpoint: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    s3_bucket: Optional[str] = None
    s3_region: Optional[str] = None
    s3_url_style: Optional[str] = None
    s3_base_path: Optional[str] = None
    s3_custom_domain: Optional[str] = None
    s3_url_suffix: Optional[str] = None


class StorageConfigResponse(BaseModel):
    backend: Optional[str] = None
    storage_base_url: Optional[str] = None
    s3_endpoint: Optional[str] = None
    s3_access_key: Optional[str] = None      # 脱敏 "***" 或 None
    has_access_key: bool = False
    s3_secret_key: Optional[str] = None      # 脱敏 "***" 或 None
    has_secret: bool = False
    s3_bucket: Optional[str] = None
    s3_region: Optional[str] = None
    s3_url_style: Optional[str] = None
    s3_base_path: Optional[str] = None
    s3_custom_domain: Optional[str] = None
    s3_url_suffix: Optional[str] = None
    sources: dict = {}


def _get_db_row(db: Session):
    return db.query(StorageConfiguration).first()


def _upsert_db(db: Session, data: dict) -> StorageConfiguration:
    row = _get_db_row(db)
    if not row:
        row = StorageConfiguration()
        db.add(row)
    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def _probe_s3(cfg) -> tuple[bool, Optional[str]]:
    """用给定配置建临时 S3Backend，put/get/delete 探针对象。返 (ok, error)。"""
    try:
        from app.services.storage.s3 import S3Backend
        b = S3Backend(endpoint=cfg.s3_endpoint, bucket=cfg.s3_bucket,
                      access_key=cfg.s3_access_key, secret_key=cfg.s3_secret_key,
                      region=cfg.s3_region, url_style=cfg.s3_url_style or "path",
                      base_path=cfg.s3_base_path or "", custom_domain=cfg.s3_custom_domain or "",
                      url_suffix=cfg.s3_url_suffix or "")
        key = "_storage_probe_test"
        b.put(key, b"ok", "application/octet-stream")
        b.get(key)
        b.delete(key)
        return True, None
    except Exception as e:
        return False, str(e)


@router.get("", response_model=StorageConfigResponse)
def get_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> StorageConfigResponse:
    cfg = load_effective_storage_config()
    return StorageConfigResponse(
        backend=cfg.backend,
        storage_base_url=cfg.storage_base_url,
        s3_endpoint=cfg.s3_endpoint,
        s3_access_key="***" if cfg.s3_access_key else None,
        has_access_key=bool(cfg.s3_access_key),
        s3_secret_key="***" if cfg.s3_secret_key else None,
        has_secret=bool(cfg.s3_secret_key),
        s3_bucket=cfg.s3_bucket,
        s3_region=cfg.s3_region,
        s3_url_style=cfg.s3_url_style,
        s3_base_path=cfg.s3_base_path,
        s3_custom_domain=cfg.s3_custom_domain,
        s3_url_suffix=cfg.s3_url_suffix,
        sources=cfg.sources,
    )


@router.put("")
def put_config(
    payload: StorageConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    data = payload.model_dump(exclude_unset=True)
    existing = _get_db_row(db)
    # 凭证「不变」哨兵：null/None 沿用旧值，不清空
    for cred in ("s3_access_key", "s3_secret_key"):
        if data.get(cred) in (None, "***"):
            data.pop(cred, None)
            if existing is not None and getattr(existing, cred, None):
                data[cred] = getattr(existing, cred)
    # 仅 backend=s3 时写前探针
    target_backend = data.get("backend") or (existing.backend if existing else "local")
    if target_backend == "s3":
        existing_endpoint = existing.s3_endpoint if existing else ""
        existing_bucket = existing.s3_bucket if existing else ""
        existing_url_style = existing.s3_url_style if existing else "path"

        probe_cfg = StorageConfigTest(
            backend="s3",
            s3_endpoint=data.get("s3_endpoint") or existing_endpoint,
            s3_access_key=data.get("s3_access_key"),
            s3_secret_key=data.get("s3_secret_key"),
            s3_bucket=data.get("s3_bucket") or existing_bucket,
            s3_region=data.get("s3_region"),
            s3_url_style=data.get("s3_url_style") or existing_url_style,
            s3_base_path=data.get("s3_base_path") or (existing.s3_base_path if existing else ""),
            s3_custom_domain=data.get("s3_custom_domain") or (existing.s3_custom_domain if existing else ""),
            s3_url_suffix=data.get("s3_url_suffix") or (existing.s3_url_suffix if existing else ""),
        )
        ok, err = _probe_s3(probe_cfg)
        if not ok:
            raise HTTPException(status_code=400, detail=f"S3 配置校验失败：{err}")
    _upsert_db(db, data)
    reset_storage()
    return {"ok": True}


@router.post("/test")
def test_config(
    payload: StorageConfigTest,
    current_user: User = Depends(get_current_admin_user),
):
    if payload.backend != "s3":
        return {"ok": True, "error": None}
    ok, err = _probe_s3(payload)
    return {"ok": ok, "error": err}


@router.post("/migrate")
def migrate(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """触发双向异步迁移。body: {direction: 'to_s3'|'to_local', s3_config?: {...}}"""
    from app.services.storage.migrate import start_migrate_task
    direction = payload.get("direction", "to_s3")
    s3_config = payload.get("s3_config")
    task_id = start_migrate_task(db, direction, s3_config, user_id=current_user.id)
    return {"task_id": task_id}
