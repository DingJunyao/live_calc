from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SmtpConfigResponse(BaseModel):
    host: str
    port: int
    username: str
    use_tls: bool
    from_address: str
    from_name: str
    enabled: bool

    model_config = {"from_attributes": True}


class SmtpConfigUpdate(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    use_tls: Optional[bool] = None
    from_address: Optional[str] = None
    from_name: Optional[str] = None
    enabled: Optional[bool] = None


class SmtpTestRequest(BaseModel):
    to_email: str


class EmailTemplateResponse(BaseModel):
    key: str
    name: str
    subject: str
    body_html: str
    description: str
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EmailTemplateUpdate(BaseModel):
    subject: Optional[str] = None
    body_html: Optional[str] = None
    description: Optional[str] = None
