from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.user import User
from app.models.invite_code import InviteCode, generate_invite_code, ensure_utc
from app.schemas.invite_code import (
    InviteCodeCreate,
    InviteCodeUpdate,
    InviteCodeResponse,
    InviteCodeUseRequest,
)
from app.schemas.common import PaginatedResponse
from app.config import settings
from typing import Optional


router = APIRouter()


def _serialize_invite_code(code: InviteCode) -> dict:
    """序列化 InviteCode 为字典。

    时间字段统一以 UTC aware ISO 输出（带时区），前端按本地时区渲染。
    """
    return {
        "id": code.id,
        "code": code.code,
        "createdBy": code.created_by,
        "usedCount": code.used_count,
        "maxUses": code.max_uses,
        "createdAt": ensure_utc(code.created_at).isoformat() if code.created_at else None,
        "expiresAt": ensure_utc(code.expires_at).isoformat() if code.expires_at else None,
    }


@router.post("", response_model=InviteCodeResponse)
async def create_invite_code(
    invite_code_data: InviteCodeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """创建邀请码 - 仅限管理员。

    可手动指定 code（不传则随机生成），可指定 max_uses（不传则不限次数）。
    """
    # 确定邀请码
    if invite_code_data.code:
        code_str = invite_code_data.code.strip()
        if db.query(InviteCode).filter(InviteCode.code == code_str).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邀请码已存在",
            )
    else:
        # 自动生成唯一码（冲突重试）
        for _ in range(5):
            code_str = generate_invite_code(settings.invite_code_length)
            if not db.query(InviteCode).filter(InviteCode.code == code_str).first():
                break

    invite_code = InviteCode(
        code=code_str,
        created_by=current_user.id,
        max_uses=invite_code_data.max_uses,
        expires_at=invite_code_data.expires_at,
    )

    db.add(invite_code)
    db.commit()
    db.refresh(invite_code)

    return invite_code


@router.get("", response_model=PaginatedResponse)
async def get_invite_codes(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="每页记录数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """获取邀请码列表（分页）- 仅限管理员"""
    invite_codes = db.query(InviteCode).order_by(InviteCode.created_at.desc())
    total = invite_codes.count()
    items = invite_codes.offset(skip).limit(limit).all()

    page = skip // limit + 1

    return PaginatedResponse.create(
        items=[_serialize_invite_code(c) for c in items],
        total=total,
        page=page,
        page_size=limit,
    )


@router.put("/{invite_code_id}", response_model=InviteCodeResponse)
async def update_invite_code(
    invite_code_id: int,
    update_data: InviteCodeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """修改邀请码 - 仅限管理员。

    只能修改过期时间和最大使用次数，不能改 code 本身。
    """
    invite_code = db.query(InviteCode).filter(InviteCode.id == invite_code_id).first()
    if not invite_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邀请码不存在",
        )

    if update_data.expires_at is not None:
        invite_code.expires_at = update_data.expires_at
    if update_data.max_uses is not None:
        invite_code.max_uses = update_data.max_uses

    db.commit()
    db.refresh(invite_code)

    return invite_code


@router.delete("/{invite_code_id}")
async def delete_invite_code(
    invite_code_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """删除邀请码 - 仅限管理员"""
    invite_code = db.query(InviteCode).filter(InviteCode.id == invite_code_id).first()
    if not invite_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邀请码不存在",
        )

    db.delete(invite_code)
    db.commit()

    return {"detail": "邀请码删除成功"}
