"""
食材层级关系管理API
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.security import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.ingredient_hierarchy import IngredientHierarchy, HierarchyRelationType
from app.models.ingredient_merge_record import IngredientMergeRecord
from app.models.nutrition import Ingredient
from app.services.ingredient_merger import IngredientMerger
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

# Pydantic 模型
class HierarchyRelationCreate(BaseModel):
    parent_id: int
    child_id: int
    relation_type: str  # "contains", "substitutable", "fallback"
    strength: Optional[int] = 50

class HierarchyRelationResponse(BaseModel):
    id: int
    parent_id: int
    parent_name: str
    child_id: int
    child_name: str
    relation_type: str
    strength: int
    created_at: datetime

class IngredientMergeRequest(BaseModel):
    source_ingredient_ids: List[int]
    target_ingredient_id: int

class IngredientMergeResponse(BaseModel):
    success: bool
    message: str
    merged_count: int
    updated_recipes_count: int
    updated_products_count: int
    updated_mappings_count: int
    stats_change: dict

class HierarchyRelationsResponse(BaseModel):
    parent_relations: List[HierarchyRelationResponse]
    child_relations: List[HierarchyRelationResponse]

class MergeRecordResponse(BaseModel):
    id: int
    source_ingredient_id: int
    source_ingredient_name: str
    target_ingredient_id: int
    target_ingredient_name: str
    merged_by_user_id: int
    merged_by_username: str
    created_at: datetime

class MergeHistoryResponse(BaseModel):
    records: List[MergeRecordResponse]

class MergeStatusResponse(BaseModel):
    is_merged: bool
    merged_into_id: Optional[int]
    merged_into_name: Optional[str]
    original_name: str


# 食材层级关系管理接口
@router.post("/ingredients/hierarchy", response_model=HierarchyRelationResponse)
def create_hierarchy_relation(
    relation: HierarchyRelationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建食材层级关系
    """
    # 验证关系类型
    try:
        relation_type = HierarchyRelationType(relation.relation_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的关系类型: {relation.relation_type}")

    # 验证食材ID是否存在
    parent_ingredient = db.query(Ingredient).filter(Ingredient.id == relation.parent_id).first()
    if not parent_ingredient:
        raise HTTPException(status_code=404, detail=f"父食材ID {relation.parent_id} 不存在")

    child_ingredient = db.query(Ingredient).filter(Ingredient.id == relation.child_id).first()
    if not child_ingredient:
        raise HTTPException(status_code=404, detail=f"子食材ID {relation.child_id} 不存在")

    # 检查是否已存在相同的关系
    existing_relation = db.query(IngredientHierarchy).filter(
        IngredientHierarchy.parent_id == relation.parent_id,
        IngredientHierarchy.child_id == relation.child_id
    ).first()

    if existing_relation:
        raise HTTPException(status_code=400, detail="该层级关系已存在")

    # 创建层级关系
    hierarchy_relation = IngredientHierarchy(
        parent_id=relation.parent_id,
        child_id=relation.child_id,
        relation_type=relation.relation_type,
        strength=relation.strength
    )

    db.add(hierarchy_relation)
    db.commit()
    db.refresh(hierarchy_relation)

    # 返回包含食材名称的完整信息
    return HierarchyRelationResponse(
        id=hierarchy_relation.id,
        parent_id=hierarchy_relation.parent_id,
        parent_name=parent_ingredient.name,
        child_id=hierarchy_relation.child_id,
        child_name=child_ingredient.name,
        relation_type=hierarchy_relation.relation_type,
        strength=hierarchy_relation.strength,
        created_at=hierarchy_relation.created_at
    )


@router.get("/ingredients/{ingredient_id}/hierarchy", response_model=HierarchyRelationsResponse)
def get_ingredient_hierarchy(
    ingredient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取食材的层级关系（作为父节点和子节点的关系）
    """
    # 获取作为父节点的关系（child relations）
    child_relations = db.query(IngredientHierarchy).filter(
        IngredientHierarchy.parent_id == ingredient_id
    ).all()

    child_responses = []
    for rel in child_relations:
        child_ingredient = db.query(Ingredient).filter(Ingredient.id == rel.child_id).first()
        if child_ingredient:
            child_responses.append(HierarchyRelationResponse(
                id=rel.id,
                parent_id=rel.parent_id,
                parent_name=child_ingredient.name,  # 这里应该是parent_ingredient，修正
                child_id=rel.child_id,
                child_name=child_ingredient.name,
                relation_type=rel.relation_type,
                strength=rel.strength,
                created_at=rel.created_at
            ))

    # 获取作为子节点的关系（parent relations）
    parent_relations = db.query(IngredientHierarchy).filter(
        IngredientHierarchy.child_id == ingredient_id
    ).all()

    parent_responses = []
    for rel in parent_relations:
        parent_ingredient = db.query(Ingredient).filter(Ingredient.id == rel.parent_id).first()
        if parent_ingredient:
            parent_responses.append(HierarchyRelationResponse(
                id=rel.id,
                parent_id=rel.parent_id,
                parent_name=parent_ingredient.name,
                child_id=rel.child_id,
                child_name=parent_ingredient.name,  # 这里应该是child_ingredient，修正
                relation_type=rel.relation_type,
                strength=rel.strength,
                created_at=rel.created_at
            ))

    # 修正上述错误
    child_responses = []
    for rel in child_relations:
        parent_ingredient = db.query(Ingredient).filter(Ingredient.id == rel.parent_id).first()
        child_ingredient = db.query(Ingredient).filter(Ingredient.id == rel.child_id).first()
        if parent_ingredient and child_ingredient:
            child_responses.append(HierarchyRelationResponse(
                id=rel.id,
                parent_id=rel.parent_id,
                parent_name=parent_ingredient.name,
                child_id=rel.child_id,
                child_name=child_ingredient.name,
                relation_type=rel.relation_type,
                strength=rel.strength,
                created_at=rel.created_at
            ))

    parent_responses = []
    for rel in parent_relations:
        parent_ingredient = db.query(Ingredient).filter(Ingredient.id == rel.parent_id).first()
        child_ingredient = db.query(Ingredient).filter(Ingredient.id == rel.child_id).first()
        if parent_ingredient and child_ingredient:
            parent_responses.append(HierarchyRelationResponse(
                id=rel.id,
                parent_id=rel.parent_id,
                parent_name=parent_ingredient.name,
                child_id=rel.child_id,
                child_name=child_ingredient.name,
                relation_type=rel.relation_type,
                strength=rel.strength,
                created_at=rel.created_at
            ))

    return HierarchyRelationsResponse(
        parent_relations=parent_responses,
        child_relations=child_responses
    )


@router.put("/ingredients/hierarchy/{relation_id}", response_model=HierarchyRelationResponse)
def update_hierarchy_relation(
    relation_id: int,
    strength: int = Body(..., embed=True, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    修改层级关系的强度
    """
    relation = db.query(IngredientHierarchy).filter(IngredientHierarchy.id == relation_id).first()
    if not relation:
        raise HTTPException(status_code=404, detail="层级关系不存在")

    # 更新强度
    relation.strength = strength
    db.commit()
    db.refresh(relation)

    # 查询相关食材信息
    parent_ingredient = db.query(Ingredient).filter(Ingredient.id == relation.parent_id).first()
    child_ingredient = db.query(Ingredient).filter(Ingredient.id == relation.child_id).first()

    if not parent_ingredient or not child_ingredient:
        raise HTTPException(status_code=404, detail="相关食材不存在")

    return HierarchyRelationResponse(
        id=relation.id,
        parent_id=relation.parent_id,
        parent_name=parent_ingredient.name,
        child_id=relation.child_id,
        child_name=child_ingredient.name,
        relation_type=relation.relation_type,
        strength=relation.strength,
        created_at=relation.created_at
    )


@router.delete("/ingredients/hierarchy/{relation_id}")
def delete_hierarchy_relation(
    relation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除层级关系
    """
    relation = db.query(IngredientHierarchy).filter(IngredientHierarchy.id == relation_id).first()
    if not relation:
        raise HTTPException(status_code=404, detail="层级关系不存在")

    db.delete(relation)
    db.commit()

    return {"message": "层级关系删除成功"}


# 食材合并功能接口
@router.post("/ingredients/merge", response_model=IngredientMergeResponse)
def merge_ingredients(
    merge_request: IngredientMergeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    合并食材 - 将多个源食材合并到目标食材
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="只有管理员可以执行食材合并操作")

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

    return IngredientMergeResponse(**result)


@router.get("/ingredients/merge-history", response_model=MergeHistoryResponse)
def get_merge_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取食材合并历史记录
    """
    records = db.query(IngredientMergeRecord).order_by(IngredientMergeRecord.created_at.desc()).all()

    responses = []
    for record in records:
        source_ingredient = db.query(Ingredient).filter(Ingredient.id == record.source_ingredient_id).first()
        target_ingredient = db.query(Ingredient).filter(Ingredient.id == record.target_ingredient_id).first()
        merged_by_user = db.query(User).filter(User.id == record.merged_by_user_id).first()

        if source_ingredient and target_ingredient and merged_by_user:
            responses.append(MergeRecordResponse(
                id=record.id,
                source_ingredient_id=record.source_ingredient_id,
                source_ingredient_name=source_ingredient.name,
                target_ingredient_id=record.target_ingredient_id,
                target_ingredient_name=target_ingredient.name,
                merged_by_user_id=record.merged_by_user_id,
                merged_by_username=merged_by_user.username,
                created_at=record.created_at
            ))

    return MergeHistoryResponse(records=responses)


@router.get("/ingredients/{ingredient_id}/merge-status", response_model=MergeStatusResponse)
def get_ingredient_merge_status(
    ingredient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取食材的合并状态
    """
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="食材不存在")

    is_merged = ingredient.is_merged
    merged_into_id = ingredient.merged_into_id
    merged_into_name = None

    if merged_into_id:
        target_ingredient = db.query(Ingredient).filter(Ingredient.id == merged_into_id).first()
        if target_ingredient:
            merged_into_name = target_ingredient.name

    return MergeStatusResponse(
        is_merged=is_merged,
        merged_into_id=merged_into_id,
        merged_into_name=merged_into_name,
        original_name=ingredient.name
    )