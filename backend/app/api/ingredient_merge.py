from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.core.database import get_db
from app.models.user import User  # 从models导入User
from app.services.ingredient_merger import IngredientMerger
from app.schemas.ingredient_merge import IngredientMergeRequest, IngredientMergeResponse  # 从ingredient_merge导入
from typing import List

router = APIRouter()


@router.post("/ingredients/merge", response_model=IngredientMergeResponse)
def merge_ingredients(
    merge_request: IngredientMergeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    合并食材 - 将多个源食材合并到目标食材

    Args:
        merge_request: 合并请求，包含源食材ID列表和目标食材ID
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        合并结果信息
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="未授权访问")

    if not merge_request.source_ingredient_ids or not merge_request.target_ingredient_id:
        raise HTTPException(status_code=400, detail="缺少必要的参数：源食材ID列表和目标食材ID")

    if merge_request.target_ingredient_id in merge_request.source_ingredient_ids:
        raise HTTPException(status_code=400, detail="目标食材不能同时是源食材")

    merger = IngredientMerger(db)
    result = merger.merge_ingredients(
        source_ingredient_ids=merge_request.source_ingredient_ids,
        target_ingredient_id=merge_request.target_ingredient_id,
        merged_by_user_id=current_user.id
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    # 确保返回的结果符合响应模型
    return IngredientMergeResponse(**result)