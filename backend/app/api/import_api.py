"""导入 API 路由。"""
import os

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.importer.api_service import (
    import_from_git_repo,
    import_from_upload,
    import_from_local_dir,
)
from app.services.importer.ai_inference.inferrer import AIInferrer

router = APIRouter()


@router.post("/data/upload")
async def upload_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """上传压缩包导入数据。

    管理员可上传 HowToCook_json 格式和系统导出格式。
    普通用户仅可上传系统导出格式。
    """
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(400, detail="仅支持 ZIP 格式的压缩包")

    try:
        result = import_from_upload(
            db, file, current_user.id, getattr(current_user, "is_admin", False)
        )
    except PermissionError as e:
        raise HTTPException(403, detail=str(e))
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=f"导入失败: {str(e)}")

    return {
        "success": len(result.errors) == 0,
        "stats": result.stats,
        "warnings": result.warnings,
        "errors": result.errors,
    }


@router.post("/data/import-from-repo")
async def trigger_repo_import(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """手动触发从 git 仓库导入（仅管理员）。"""
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(403, detail="仅管理员可操作")

    try:
        result = import_from_git_repo(db, current_user.id)
    except Exception as e:
        raise HTTPException(500, detail=f"导入失败: {str(e)}")

    return {
        "success": len(result.errors) == 0,
        "stats": result.stats,
        "warnings": result.warnings,
        "errors": result.errors,
    }


@router.post("/data/import-from-local")
async def trigger_local_import(
    local_path: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """从本地目录导入（仅管理员）。"""
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(403, detail="仅管理员可操作")

    if not os.path.isdir(local_path):
        raise HTTPException(400, detail=f"目录不存在: {local_path}")

    try:
        result = import_from_local_dir(db, local_path, current_user.id)
    except Exception as e:
        raise HTTPException(500, detail=f"导入失败: {str(e)}")

    return {
        "success": len(result.errors) == 0,
        "stats": result.stats,
        "warnings": result.warnings,
        "errors": result.errors,
    }


# ---- AI 后处理端点 ----


@router.post("/ai-infer/quantities")
async def infer_fuzzy_quantities(
    force: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """触发模糊量推测。"""
    inferrer = AIInferrer(db)
    result = inferrer.infer_fuzzy_quantities(force=force)

    return {
        "success": len(result.errors) == 0,
        "stats": result.stats,
        "warnings": result.warnings,
        "errors": result.errors,
    }


@router.post("/ai-infer/densities")
async def infer_densities(
    force: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """触发密度推测。"""
    inferrer = AIInferrer(db)
    result = inferrer.infer_densities(force=force)

    return {
        "success": len(result.errors) == 0,
        "stats": result.stats,
        "warnings": result.warnings,
        "errors": result.errors,
    }
