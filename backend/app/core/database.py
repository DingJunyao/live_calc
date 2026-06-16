from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.config import settings

# 创建引擎
_sqlite_connect_args = {}
if "sqlite" in settings.database_url:
    _sqlite_connect_args["check_same_thread"] = False
    # busy_timeout：写锁被占时连接等待最多 30 秒，避免后台长写任务期间其他请求立即 database is locked
    _sqlite_connect_args["timeout"] = 30

engine = create_engine(
    settings.database_url,
    connect_args=_sqlite_connect_args,
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
