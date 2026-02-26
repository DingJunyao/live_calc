from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class InviteCodeBase(BaseModel):
    code: str
    used: bool = False


class InviteCodeCreate(BaseModel):
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