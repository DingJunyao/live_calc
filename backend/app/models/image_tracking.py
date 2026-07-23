from sqlalchemy import Column, String, Integer, DateTime, func
from app.core.database import Base


class ImageTracking(Base):
    """图片引用追踪。

    记录每个存储 key 的引用次数、文件大小、内容哈希和最近使用时间，
    用于图片 GC 判定与存储用量统计。
    """

    __tablename__ = "image_tracking"

    key = Column(String(512), primary_key=True)
    ref_count = Column(Integer, default=0, nullable=False)
    file_size = Column(Integer, default=0, nullable=False)
    content_hash = Column(String(64), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
