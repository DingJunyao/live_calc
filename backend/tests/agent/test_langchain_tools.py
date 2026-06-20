"""只读 @tool 单测：查库正确 + db_read 拒非 SELECT。"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.services.agent.langchain_tools import db_read, describe, list_tables


@pytest.fixture()
def mem_db(monkeypatch):
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    with eng.connect() as conn:
        conn.execute(text("CREATE TABLE t (id INTEGER PRIMARY KEY, x INTEGER)"))
        conn.execute(text("INSERT INTO t (id, x) VALUES (1, 100), (2, 200)"))
        conn.commit()
    TestSession = sessionmaker(bind=eng, autoflush=False, autocommit=False)
    import app.core.database as dbmod

    monkeypatch.setattr(dbmod, "SessionLocal", TestSession)
    yield TestSession
    eng.dispose()


def test_db_read_select_returns_rows(mem_db):
    out = db_read.invoke({"sql": "SELECT id, x FROM t ORDER BY id"})
    assert "100" in out and "200" in out


def test_db_read_rejects_non_select(mem_db):
    out = db_read.invoke({"sql": "DELETE FROM t WHERE id=1"})
    assert out.startswith("拒绝执行")
    db = mem_db()
    try:
        assert db.execute(text("SELECT COUNT(*) FROM t")).scalar() == 2
    finally:
        db.close()


def test_list_tables_returns_t(mem_db):
    out = list_tables.invoke({})
    assert "t" in out


def test_describe_returns_columns(mem_db):
    out = describe.invoke({"table_name": "t"})
    assert "id" in out and "x" in out
