"""导入 API 路由。"""
import os

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usda import TranslationConfig
from app.services.importer.api_service import (
    import_from_git_repo,
    import_from_upload,
    import_from_local_dir,
)
from app.services.importer.ai_inference.inferrer import AIInferrer

router = APIRouter()


@router.post("/data/upload")
def upload_import(
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
def trigger_repo_import(
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
def trigger_local_import(
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


def _create_ai_caller(provider: str, db: Session):
    """根据 provider 名称创建 AI 调用函数。

    从 TranslationConfig 中读取该 provider 的配置并构造 Translator，
    返回一个同步的 callable(prompt: str) -> str。
    如果 provider 不可用则返回 None。
    """
    try:
        cfg_record = db.query(TranslationConfig).first()
        if not cfg_record:
            return None
        config_dict = cfg_record.to_dict()

        # 在 ai 和 machine 两区中查找 provider 配置
        from app.services.translate.registry import get_translator, find_provider_section
        prov_cfg = find_provider_section(config_dict, provider)
        if not prov_cfg:
            return None

        import asyncio
        translator = get_translator(provider, prov_cfg, timeout=120)

        def _call(prompt: str) -> str:
            """同步调用 translator 的 translate_batch。"""
            result_list = asyncio.run(
                translator.translate_batch([prompt])
            )
            return result_list[0] if result_list else ""

        # 快速健康检查
        try:
            test = _call("回复一个词：ok")
            if not test:
                return None
        except Exception:
            return None

        return _call
    except Exception:
        return None


@router.post("/ai-infer/quantities")
def infer_fuzzy_quantities(
    force: bool = False,
    provider: str = Query("claude_code", description="AI 提供方名称"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """触发模糊量推测。

    需要先在 AI 配置页启用至少一个 AI 后端。
    通过 provider 参数指定使用的 AI 提供方。
    """
    ai_caller = _create_ai_caller(provider, db)
    inferrer = AIInferrer(db)
    if ai_caller:
        inferrer.set_ai_caller(ai_caller)

    result = inferrer.infer_fuzzy_quantities(force=force)

    if not ai_caller and len(result.warnings) == 0:
        result.warnings.append(
            f"AI 后端 '{provider}' 不可用，跳过 AI 推测。"
            "请先在 AI 配置页启用并测试连接。"
        )

    return {
        "success": len(result.errors) == 0,
        "stats": result.stats,
        "warnings": result.warnings,
        "errors": result.errors,
    }


@router.post("/ai-infer/densities")
def infer_densities(
    force: bool = False,
    provider: str = Query("claude_code", description="AI 提供方名称"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """触发密度推测。

    需要先在 AI 配置页启用至少一个 AI 后端。
    通过 provider 参数指定使用的 AI 提供方。
    """
    ai_caller = _create_ai_caller(provider, db)
    inferrer = AIInferrer(db)
    if ai_caller:
        inferrer.set_ai_caller(ai_caller)

    result = inferrer.infer_densities(force=force)

    if not ai_caller and len(result.warnings) == 0:
        result.warnings.append(
            f"AI 后端 '{provider}' 不可用，跳过 AI 推测。"
            "请先在 AI 配置页启用并测试连接。"
        )

    return {
        "success": len(result.errors) == 0,
        "stats": result.stats,
        "warnings": result.warnings,
        "errors": result.errors,
    }
