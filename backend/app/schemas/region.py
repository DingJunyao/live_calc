"""行政区划 Pydantic 响应模型"""

from pydantic import BaseModel
from typing import Optional


class RegionResponse(BaseModel):
    """单条行政区划响应"""
    id: int
    code: str
    name: str
    name_en: Optional[str] = None
    level: int
    iso_country: Optional[str] = None
    path: Optional[str] = None
    has_children: bool = False

    model_config = {"from_attributes": True}


class RegionAncestor(BaseModel):
    """祖先节点"""
    id: int
    code: str
    name: str
    level: int


class RegionDetailResponse(RegionResponse):
    """行政区划详情响应（含祖先链）"""
    ancestors: list[RegionAncestor] = []
