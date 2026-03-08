from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.invite_code import InviteCode, generate_invite_code
from app.schemas.invite_code import InviteCodeCreate, InviteCodeResponse, InviteCodeUseRequest
from app.schemas.common import PaginatedResponse
from app.config import settings
import datetime


router = APIRouter()


@router.post("", response_model=InviteCodeResponse)
async def create_invite_code(
    invite_code_data: InviteCodeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建邀请码 - 仅限管理员"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅限管理员访问"
        )

    # 生成唯一邀请码
    code = generate_invite_code(settings.invite_code_length)

    # 检查是否已存在（虽然概率极低，但为了安全起见）
    existing_code = db.query(InviteCode).filter(InviteCode.code == code).first()
    if existing_code:
        # 如果意外冲突，再生成一次
        code = generate_invite_code(settings.invite_code_length)

    invite_code = InviteCode(
        code=code,
        created_by=current_user.id,
        expires_at=invite_code_data.expires_at
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
    current_user: User = Depends(get_current_user)
):
    """获取邀请码列表（分页）- 仅限管理员"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅限管理员访问"
        )

    invite_codes = db.query(InviteCode).order_by(InviteCode.created_at.desc())
    total = invite_codes.count()
    items = invite_codes.offset(skip).limit(limit).all()

    page = skip // limit + 1

    return PaginatedResponse.create(
        items=[{
            "id": code.id,
            "code": code.code,
            "createdBy": code.created_by,
            "used": code.used,
            "createdAt": code.created_at.strftime('%Y-%m-%dT%H:%M:%S'),
            "expiresAt": code.expires_at.strftime('%Y-%m-%dT%H:%M:%S') if code.expires_at else None
        } for code in items],
        total=total,
        page=page,
        page_size=limit
    )


@router.delete("/{invite_code_id}")
async def delete_invite_code(
    invite_code_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除邀请码 - 仅限管理员"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅限管理员访问"
        )

    invite_code = db.query(InviteCode).filter(InviteCode.id == invite_code_id).first()
    if not invite_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邀请码不存在"
        )

    db.delete(invite_code)
    db.commit()

    return {"detail": "邀请码删除成功"}


def validate_invite_code(code: str, db: Session) -> bool:
    """验证邀请码是否有效"""
    invite_code = db.query(InviteCode).filter(InviteCode.code == code).first()

    if not invite_code:
        return False

    # 检查是否已使用
    if invite_code.used:
        return False

    # 检查是否已过期
    if invite_code.expires_at and invite_code.expires_at < datetime.datetime.now(datetime.timezone.utc):
        return False

    # 标记为已使用
    invite_code.used = True
    db.commit()

    return True