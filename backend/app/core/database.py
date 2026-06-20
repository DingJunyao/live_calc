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

# pool_size / max_overflow: Agent 会话（run_agent_loop）会持有一个连接直到会话结束。
# 增大池容量防止多个并发 Agent 耗尽连接；pool_pre_ping 检测失效连接。
_sqlite_pool_args = {}
if "sqlite" in settings.database_url:
    # SQLite 的 QueuePool 默认 pool_size=5, max_overflow=10——Agent 场景不够用。
    # pool_size=10 可容纳约 5 个长 Agent + 5 个短 API 请求同时运作。
    _sqlite_pool_args["pool_size"] = 10
    _sqlite_pool_args["max_overflow"] = 20

engine = create_engine(
    settings.database_url,
    connect_args=_sqlite_connect_args,
    pool_pre_ping=True,
    **_sqlite_pool_args,
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
