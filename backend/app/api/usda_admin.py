# backend/app/api/usda_admin.py
"""USDA 管理路由（admin only）：下载 / 上传 / 任务 / 统计 / 未映射清单。"""
import io
import json
import logging
import traceback
import zipfile

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

from pydantic import BaseModel

from app.config import settings
from app.core.database import get_db, SessionLocal
from app.core.security import get_current_user
from app.models.usda import UsdaFood, UsdaFoodNutrient, UsdaTask, TranslationConfig
from app.services.usda.importer import UsdaImporter
from app.services.usda.parser import parse_usda_food, dedupe_foods
from app.services.usda.index_manager import build_usda_index
from app.services.translate.registry import find_provider_section, get_translator
from app.services.translate.task import TranslateTask
from app.services.translate.nutrient_task import TranslateNutrientsTask

router = APIRouter()


def _require_admin(current_user) -> None:
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="仅限管理员访问")


DEFAULT_TRANSLATION_CONFIG = {
    "ai": {"providers": {
        "claude_code": {"enabled": False},
        "openai": {"enabled": False, "base_url": "https://api.openai.com/v1", "api_key": "", "model": "gpt-4o-mini"},
        "anthropic": {"enabled": False, "base_url": "https://api.anthropic.com", "api_key": "", "model": "claude-sonnet-4-6"},
    }},
    "machine": {"providers": {
        "baidu": {"enabled": False, "appid": "", "secret": ""},
        "aliyun": {"enabled": False, "access_key_id": "", "access_key_secret": ""},
        "deepl": {"enabled": False, "auth_key": ""},
    }},
}


def get_stored_translation_config(db: Session) -> TranslationConfig:
    """获取翻译配置，不存在则创建默认。"""
    cfg = db.query(TranslationConfig).first()
    if not cfg:
        cfg = TranslationConfig(config=DEFAULT_TRANSLATION_CONFIG)
        db.add(cfg); db.commit(); db.refresh(cfg)
    return cfg


class TranslationConfigUpdate(BaseModel):
    config: dict


class TranslateRequest(BaseModel):
    provider: str


class TestConnectionRequest(BaseModel):
    provider: str


@router.get("/usda/statistics")
async def usda_statistics(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_admin(current_user)
    from sqlalchemy import func

    total = db.query(func.count(UsdaFood.id)).scalar() or 0
    translated = (
        db.query(func.count(UsdaFood.id))
        .filter(UsdaFood.translate_status == "done")
        .scalar()
        or 0
    )
    pending = (
        db.query(func.count(UsdaFood.id))
        .filter(UsdaFood.translate_status == "pending")
        .scalar()
        or 0
    )
    error = (
        db.query(func.count(UsdaFood.id))
        .filter(UsdaFood.translate_status == "error")
        .scalar()
        or 0
    )
    nutrients = db.query(func.count(UsdaFoodNutrient.id)).scalar() or 0
    unmapped = (
        db.query(func.count(UsdaFoodNutrient.id))
        .filter(UsdaFoodNutrient.name_zh.is_(None))
        .scalar()
        or 0
    )
    return {
        "total": total,
        "translated": translated,
        "pending": pending,
        "error": error,
        "nutrients": nutrients,
        "unmapped_nutrients": unmapped,
    }


@router.get("/usda/unmapped-nutrients")
async def unmapped_nutrients(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_admin(current_user)
    from sqlalchemy import distinct

    names = [
        r[0]
        for r in db.query(distinct(UsdaFoodNutrient.name))
        .filter(UsdaFoodNutrient.name_zh.is_(None))
        .all()
    ]
    return {"names": sorted(names), "count": len(names)}


def _do_download(db_factory, datasets):
    """后台任务：下载 → 入库 → 重建索引 → 更新 task。"""
    db = db_factory()
    task = UsdaTask(task_type="download", status="running")
    db.add(task)
    db.commit()
    db.refresh(task)
    try:
        from app.services.usda.downloader import download_all

        foods = download_all(datasets)
        result = UsdaImporter(db).import_entries(foods)
        build_usda_index(db)
        task.status = "success"
        task.progress = {"foods": len(foods), **result}
    except Exception as e:
        logging.getLogger(__name__).exception("USDA 下载任务失败")
        task.status = "failed"
        task.error_log = traceback.format_exc()
    finally:
        db.commit()
        db.close()


@router.post("/usda/download")
async def usda_download(
    background_tasks: BackgroundTasks,
    datasets: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_admin(current_user)
    ds_list = datasets.split(",") if datasets else None
    background_tasks.add_task(_do_download, SessionLocal, ds_list)
    return {"message": "下载任务已启动"}


@router.post("/usda/upload")
async def usda_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    content = await file.read()
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            json_name = next(n for n in zf.namelist() if n.endswith(".json"))
            with zf.open(json_name) as f:
                data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无法解析上传文件: {e}")
    key_map = {"FoundationFoods": "foundation", "SRLegacyFoods": "sr_legacy"}
    foods = []
    for key, dtype in key_map.items():
        if key in data:
            foods.extend(parse_usda_food(r, data_type=dtype) for r in data[key] if r is not None)
    deduped = dedupe_foods(foods)

    def _run():
        d = SessionLocal()
        task = UsdaTask(task_type="upload", status="running")
        d.add(task)
        d.commit()
        d.refresh(task)
        try:
            res = UsdaImporter(d).import_entries(deduped)
            build_usda_index(d)
            task.status = "success"
            task.progress = {"foods": len(deduped), **res}
        except Exception as e:
            logging.getLogger(__name__).exception("USDA 上传任务失败")
            task.status = "failed"
            task.error_log = traceback.format_exc()
        finally:
            d.commit()
            d.close()

    background_tasks.add_task(_run)
    return {"message": "上传解析任务已启动", "foods_parsed": len(deduped)}


@router.get("/usda/task")
async def usda_task(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_admin(current_user)
    latest = db.query(UsdaTask).order_by(UsdaTask.id.desc()).first()
    if not latest:
        return {"task_type": None, "status": "idle"}
    return {
        "id": latest.id,
        "task_type": latest.task_type,
        "status": latest.status,
        "progress": latest.progress,
        "provider": latest.provider,
        "error_log": latest.error_log,
    }


@router.get("/translation-config")
async def get_translation_config(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_admin(current_user)
    return get_stored_translation_config(db).to_dict()


@router.put("/translation-config")
async def put_translation_config(
    body: TranslationConfigUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_admin(current_user)
    cfg = get_stored_translation_config(db)
    cfg.config = body.config
    db.commit()
    db.refresh(cfg)
    return cfg.to_dict()


@router.post("/usda/translate")
async def usda_translate(
    body: TranslateRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    cfg = get_stored_translation_config(db).to_dict()
    if not find_provider_section(cfg, body.provider):
        raise HTTPException(status_code=400, detail=f"未配置 provider: {body.provider}")

    async def _run():
        d = SessionLocal()
        try:
            await TranslateTask(d).run(
                provider=body.provider,
                config_dict=get_stored_translation_config(d).to_dict(),
            )
            build_usda_index(d)
        finally:
            d.close()

    background_tasks.add_task(_run)
    return {"message": f"翻译任务已启动（{body.provider}）"}


class TranslateNutrientsRequest(BaseModel):
    provider: str


@router.post("/usda/translate-nutrients")
async def usda_translate_nutrients(
    body: TranslateNutrientsRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """用 AI 翻译未映射营养素名（缩写/脂肪酸记号等需营养学知识）。"""
    _require_admin(current_user)
    cfg = get_stored_translation_config(db).to_dict()
    if not find_provider_section(cfg, body.provider):
        raise HTTPException(status_code=400, detail=f"未配置 provider: {body.provider}")

    async def _run_nutrients():
        d = SessionLocal()
        try:
            await TranslateNutrientsTask(d).run(
                provider=body.provider,
                config_dict=get_stored_translation_config(d).to_dict(),
            )
        except Exception:
            logging.getLogger(__name__).exception("营养素翻译后台任务失败")
        finally:
            d.close()
    background_tasks.add_task(_run_nutrients)
    return {"message": f"营养素翻译任务已启动（{body.provider}）"}


@router.post("/translation-config/test")
async def translation_config_test(
    body: TestConnectionRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    cfg = get_stored_translation_config(db).to_dict()
    section = find_provider_section(cfg, body.provider)
    if not section:
        raise HTTPException(status_code=400, detail=f"未配置 provider: {body.provider}")
    translator = get_translator(body.provider, section, timeout=settings.translate_http_timeout)
    try:
        out = await translator.translate_batch(["Water"])
        ok = bool(out and out[0])
        detail = "连接成功" if ok else f"调用成功但无有效译文：{out[:3]}"
    except Exception as e:
        ok = False
        detail = f"{type(e).__name__}: {e}"
    return {"provider": body.provider, "ok": ok, "detail": detail}
