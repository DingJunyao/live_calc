"""
食材层级关系管理API
"""
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Set
from app.core.security import get_current_user, get_current_admin_user
from app.core.database import get_db
from app.models.user import User
from app.models.ingredient_hierarchy import IngredientHierarchy, HierarchyRelationType
from app.models.ingredient_merge_record import IngredientMergeRecord
from app.models.nutrition import Ingredient
from app.services.ingredient_merger import IngredientMerger
from app.services.proposals import service as proposal_service
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import or_

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

class ExpandedIngredientRelations(BaseModel):
    """某个关联食材的下一级关系"""
    ingredient_id: int
    ingredient_name: str
    parent_relations: List[HierarchyRelationResponse]
    child_relations: List[HierarchyRelationResponse]

class HierarchyRelationsResponse(BaseModel):
    parent_relations: List[HierarchyRelationResponse]
    child_relations: List[HierarchyRelationResponse]
    expanded_relations: Optional[List[ExpandedIngredientRelations]] = None

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

    分流模式：管理员 apply_as_admin（直写留痕）/ 普通用户 submit（提议，待审）。
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

    # 对于 fallback（回退）关系，需要特殊处理
    # 回退关系的语义是：从抽象原料回退到具体原料
    # 数据模型中：parent 是具体原料（数据源），child 是抽象原料
    # 例如：parent=猪肉, child=肉，表示"肉"可以回退使用"猪肉"的数据
    if relation_type == HierarchyRelationType.FALLBACK:
        actual_parent_id = relation.child_id
        actual_child_id = relation.parent_id
        if actual_parent_id == actual_child_id:
            raise HTTPException(status_code=400, detail="不能创建自引用的回退关系")
    else:
        actual_parent_id = relation.parent_id
        actual_child_id = relation.child_id

    # 检查是否已存在相同的关系（含关系类型）
    existing_relation = db.query(IngredientHierarchy).filter(
        IngredientHierarchy.parent_id == actual_parent_id,
        IngredientHierarchy.child_id == actual_child_id,
        IngredientHierarchy.relation_type == relation.relation_type
    ).first()
    if existing_relation:
        raise HTTPException(
            status_code=400,
            detail=f"该层级关系已存在（{relation_type.value}）"
        )

    payload = {
        "parent_id": actual_parent_id,
        "child_id": actual_child_id,
        "relation_type": relation.relation_type,
        "strength": relation.strength,
    }

    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="hierarchy", entity_id=None,
            action="create", payload=payload, admin=current_user,
        )
        db.commit()
        created = db.query(IngredientHierarchy).filter(
            IngredientHierarchy.parent_id == actual_parent_id,
            IngredientHierarchy.child_id == actual_child_id,
            IngredientHierarchy.relation_type == relation.relation_type,
        ).order_by(IngredientHierarchy.id.desc()).first()
        return HierarchyRelationResponse(
            id=created.id,
            parent_id=created.parent_id,
            parent_name=db.query(Ingredient).filter(Ingredient.id == created.parent_id).first().name,
            child_id=created.child_id,
            child_name=db.query(Ingredient).filter(Ingredient.id == created.child_id).first().name,
            relation_type=created.relation_type,
            strength=created.strength,
            created_at=created.created_at,
        )

    p = proposal_service.submit(
        db, entity_type="hierarchy", entity_id=None,
        action="create", payload=payload, proposer=current_user,
    )
    db.commit()
    return HierarchyRelationResponse(
        id=0,
        parent_id=actual_parent_id,
        parent_name=parent_ingredient.name,
        child_id=actual_child_id,
        child_name=child_ingredient.name,
        relation_type=relation.relation_type,
        strength=relation.strength or 50,
        created_at=p.created_at or datetime.utcnow(),
    )


@router.get("/ingredients/{ingredient_id}/hierarchy", response_model=HierarchyRelationsResponse)
def get_ingredient_hierarchy(
    ingredient_id: int,
    depth: int = Query(1, ge=1, le=3, description="层级展开深度，1=仅直接关系，2=含下一级关系"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取食材的层级关系（作为父节点和子节点的关系）
    """
    def _build_relation_response(rel: IngredientHierarchy, db: Session) -> Optional[HierarchyRelationResponse]:
        """构建单个关系的响应对象"""
        parent_ingredient = db.query(Ingredient).filter(Ingredient.id == rel.parent_id).first()
        child_ingredient = db.query(Ingredient).filter(Ingredient.id == rel.child_id).first()
        if parent_ingredient and child_ingredient:
            return HierarchyRelationResponse(
                id=rel.id,
                parent_id=rel.parent_id,
                parent_name=parent_ingredient.name,
                child_id=rel.child_id,
                child_name=child_ingredient.name,
                relation_type=rel.relation_type,
                strength=rel.strength,
                created_at=rel.created_at
            )
        return None

    # 获取作为父节点的关系（child relations）
    child_relations = db.query(IngredientHierarchy).filter(
        IngredientHierarchy.parent_id == ingredient_id
    ).all()

    child_responses = [r for r in (_build_relation_response(rel, db) for rel in child_relations) if r]

    # 获取作为子节点的关系（parent relations）
    parent_relations = db.query(IngredientHierarchy).filter(
        IngredientHierarchy.child_id == ingredient_id
    ).all()

    parent_responses = [r for r in (_build_relation_response(rel, db) for rel in parent_relations) if r]

    # 当 depth >= 2 时，展开下一级关系
    expanded_relations = None
    if depth >= 2:
        # 收集一级关系中出现的所有食材 ID（排除当前食材自身）
        visited: Set[int] = {ingredient_id}
        related_ids: Set[int] = set()
        for rel in child_responses:
            related_ids.add(rel.child_id)
            related_ids.add(rel.parent_id)
        for rel in parent_responses:
            related_ids.add(rel.parent_id)
            related_ids.add(rel.child_id)
        related_ids.discard(ingredient_id)

        expanded = []
        for rid in related_ids:
            visited.add(rid)
            rel_ingredient = db.query(Ingredient).filter(Ingredient.id == rid).first()
            if not rel_ingredient:
                continue

            # 获取该食材的直接关系，排除已访问的食材
            rel_children = db.query(IngredientHierarchy).filter(
                IngredientHierarchy.parent_id == rid
            ).all()
            rel_parents = db.query(IngredientHierarchy).filter(
                IngredientHierarchy.child_id == rid
            ).all()

            rel_child_responses = []
            for r in rel_children:
                # 排除当前食材自身（已在中心节点）和当前食材的其他一级关系
                if r.child_id not in visited:
                    resp = _build_relation_response(r, db)
                    if resp:
                        rel_child_responses.append(resp)

            rel_parent_responses = []
            for r in rel_parents:
                if r.parent_id not in visited:
                    resp = _build_relation_response(r, db)
                    if resp:
                        rel_parent_responses.append(resp)

            # 只有存在二级关系时才加入结果
            if rel_child_responses or rel_parent_responses:
                expanded.append(ExpandedIngredientRelations(
                    ingredient_id=rid,
                    ingredient_name=rel_ingredient.name,
                    parent_relations=rel_parent_responses,
                    child_relations=rel_child_responses
                ))

        expanded_relations = expanded if expanded else None

    return HierarchyRelationsResponse(
        parent_relations=parent_responses,
        child_relations=child_responses,
        expanded_relations=expanded_relations
    )


@router.put("/ingredients/hierarchy/{relation_id}", response_model=HierarchyRelationResponse)
def update_hierarchy_relation(
    relation_id: int,
    strength: int = Body(..., embed=True, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    修改层级关系的强度（分流：管理员直写 / 普通用户提议）。
    """
    relation = db.query(IngredientHierarchy).filter(IngredientHierarchy.id == relation_id).first()
    if not relation:
        raise HTTPException(status_code=404, detail="层级关系不存在")

    payload = {"strength": strength}

    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="hierarchy", entity_id=relation_id,
            action="update", payload=payload, admin=current_user,
        )
        db.commit()
        db.refresh(relation)
    else:
        p = proposal_service.submit(
            db, entity_type="hierarchy", entity_id=relation_id,
            action="update", payload=payload, proposer=current_user,
        )
        db.commit()
        # 提议路径：返回当前值（待审），不立即变更
        return HierarchyRelationResponse(
            id=relation.id,
            parent_id=relation.parent_id,
            parent_name=db.query(Ingredient).filter(Ingredient.id == relation.parent_id).first().name
            if db.query(Ingredient).filter(Ingredient.id == relation.parent_id).first() else "",
            child_id=relation.child_id,
            child_name=db.query(Ingredient).filter(Ingredient.id == relation.child_id).first().name
            if db.query(Ingredient).filter(Ingredient.id == relation.child_id).first() else "",
            relation_type=relation.relation_type,
            strength=relation.strength,
            created_at=relation.created_at,
        )

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
    删除层级关系（分流：管理员直写 / 普通用户提议）。

    注：经框架执行器走的删除为软删（is_active=False），与原 db.delete 硬删有差异，
    但便于 revert 回滚；查询侧统一按 is_active=True 过滤即可。
    """
    relation = db.query(IngredientHierarchy).filter(IngredientHierarchy.id == relation_id).first()
    if not relation:
        raise HTTPException(status_code=404, detail="层级关系不存在")

    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="hierarchy", entity_id=relation_id,
            action="delete", payload={}, admin=current_user,
        )
        db.commit()
        return {"message": "层级关系删除成功（管理员直写）"}

    p = proposal_service.submit(
        db, entity_type="hierarchy", entity_id=relation_id,
        action="delete", payload={}, proposer=current_user,
    )
    db.commit()
    return {"message": f"删除提议已提交（proposal_id={p.id}, status={p.status}）"}


# 食材合并功能接口
@router.post("/ingredients/merge", response_model=IngredientMergeResponse)
def merge_ingredients(
    merge_request: IngredientMergeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    合并食材 - 将多个源食材合并到目标食材

    分流模式：
    - 管理员：经框架 apply_as_admin 直写（留痕 change_proposals），立即生效。
    - 普通用户：经框架 submit 提议（治理总表 ingredient.merge = manual → 待审），不限制所有权。
    """
    if not merge_request.source_ingredient_ids or not merge_request.target_ingredient_id:
        raise HTTPException(status_code=400, detail="缺少必要的参数：源食材ID列表和目标食材ID")

    if merge_request.target_ingredient_id in merge_request.source_ingredient_ids:
        raise HTTPException(status_code=400, detail="目标食材不能同时是源食材")

    source_ids = merge_request.source_ingredient_ids
    target_id = merge_request.target_ingredient_id

    # 预计算影响（供审核台展示 + 响应计数）
    from app.models.recipe import RecipeIngredient
    from app.models.product_ingredient_link import ProductIngredientLink
    from app.models.nutrition import IngredientNutritionMapping

    source_names = [
        ing.name for ing in
        db.query(Ingredient).filter(Ingredient.id.in_(source_ids)).all()
    ]
    target_ing = db.query(Ingredient).get(target_id)
    target_name = target_ing.name if target_ing else f"#{target_id}"

    recipe_count = db.query(RecipeIngredient).filter(
        RecipeIngredient.ingredient_id.in_(source_ids)).count()
    product_link_count = db.query(ProductIngredientLink).filter(
        ProductIngredientLink.ingredient_id.in_(source_ids)).count()
    nutrition_count = db.query(IngredientNutritionMapping).filter(
        IngredientNutritionMapping.ingredient_id.in_(source_ids)).count()
    hierarchy_count = db.query(IngredientHierarchy).filter(or_(
        IngredientHierarchy.parent_id.in_(source_ids),
        IngredientHierarchy.child_id.in_(source_ids))).count()

    preview = {
        "sources": [{"id": sid, "name": sn} for sid, sn in zip(source_ids, source_names)],
        "target_name": target_name,
        "recipe_ingredients_count": recipe_count,
        "product_links_count": product_link_count,
        "nutrition_mappings_count": nutrition_count,
        "hierarchies_count": hierarchy_count,
    }

    payload = {
        "source_ids": source_ids,
        "target_id": target_id,
        "preview": preview,
    }

    if current_user.is_admin:
        # 管理员直写，经框架留痕（apply_as_admin 内部调执行器 apply → IngredientExecutor._apply_merge）
        proposal_service.apply_as_admin(
            db, entity_type="ingredient",
            entity_id=merge_request.target_ingredient_id,
            action="merge", payload=payload, admin=current_user,
        )
        db.commit()
        return IngredientMergeResponse(
            success=True,
            message="合并完成（管理员直写）",
            merged_count=len(source_ids),
            updated_recipes_count=recipe_count,
            updated_products_count=product_link_count,
            updated_mappings_count=nutrition_count,
            updated_hierarchies_count=hierarchy_count,
            stats_change={},
        )

    # 普通用户提交提议（治理总表 ingredient.merge = manual → 待审）
    p = proposal_service.submit(
        db, entity_type="ingredient",
        entity_id=merge_request.target_ingredient_id,
        action="merge", payload=payload, proposer=current_user,
    )
    db.commit()
    return IngredientMergeResponse(
        success=True,
        message=f"合并提议已提交，待管理员审核（proposal_id={p.id}）",
        merged_count=len(source_ids),
        updated_recipes_count=recipe_count,
        updated_products_count=product_link_count,
        updated_mappings_count=nutrition_count,
        updated_hierarchies_count=hierarchy_count,
        stats_change={},
    )


@router.get("/ingredients/merge-history", response_model=MergeHistoryResponse)
def get_merge_history(
    current_user: User = Depends(get_current_admin_user),
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