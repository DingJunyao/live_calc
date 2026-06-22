from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class InviteCodeBase(BaseModel):
    code: str
    used_count: int = 0
    max_uses: Optional[int] = None


class InviteCodeCreate(BaseModel):
    code: Optional[str] = None  # 不传则随机生成
    max_uses: Optional[int] = None  # 不传则不限次数
    expires_at: Optional[datetime] = None  # 不传则永不过期


class InviteCodeUpdate(BaseModel):
    max_uses: Optional[int] = None
    expires_at: Optional[datetime] = None


class InviteCodeResponse(InviteCodeBase):
    id: int
    created_by: Optional[int]
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class InviteCodeUseRequest(BaseModel):
    invite_code: str