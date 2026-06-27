# backend/tests/conftest.py
"""共享测试基础设施。

集中提供内存 SQLite engine 与 FakeUser，解决 `test_usda_api.py` 与
`test_usda_admin_api.py` 各自在模块级设置 `app.dependency_overrides[get_db]`
导致的隔离冲突：联合运行时后加载的 override 覆盖先加载的，使对方 fixture
数据不可见。

设计要点：
- engine 与 FakeUser 为模块级单例（一次构建，所有 USDA 测试共享同一内存库）。
- **不**在模块级注册 `app.dependency_overrides`，因为 `test_auth` / `test_products` /
  `test_locations` / `test_recipes` / `test_reports` / `test_export` 等既有测试依赖
  真实数据库（无 override）。全局 override 会破坏它们。
- 改由 `usda_app_overrides` fixture（autouse=False）按需为 USDA 测试安装 override，
  测试结束后恢复原状，做到「仅影响需要内存库的测试」。
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.core.security import get_current_user

# 共享内存 engine：StaticPool 让 TestClient 跨线程与 fixture 共享同一内存库
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(engine)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


class FakeUser:
    """满足 UserResponse 字段的占位管理员用户。"""
    id = 1
    username = "admin"
    email = "a@b.c"
    phone = None
    is_admin = True
    email_verified = True
    created_at = None


def fake_current_user():
    return FakeUser()


@pytest.fixture()
def db_session():
    """直接暴露内存库会话，供需要手写数据的测试使用。"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def usda_app_overrides():
    """为 USDA 测试安装内存库 + FakeUser override，结束后恢复。

    只在显式依赖（或被 USDA 模块级 autouse 间接请求）时生效，避免污染既有
    依赖真实数据库的测试。
    """
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = fake_current_user
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest.fixture()
def clean_usda_tables(usda_app_overrides):
    """清理 USDA 相关表的前后置，保证 USDA 测试间数据隔离。

    依赖 `usda_app_overrides` 以确保 override 已安装；只清 usda_* 四表，
    不动 NutritionData/Ingredient/Product，避免影响其他测试的留存数据。
    """
    Base.metadata.create_all(engine)
    from app.models.usda import (
        UsdaFood,
        UsdaFoodNutrient,
        TranslationConfig,
        UsdaTask,
    )
    db = TestingSessionLocal()
    try:
        db.query(UsdaTask).delete()
        db.query(TranslationConfig).delete()
        db.query(UsdaFoodNutrient).delete()
        db.query(UsdaFood).delete()
        db.commit()
    finally:
        db.close()
    yield
    db = TestingSessionLocal()
    try:
        db.query(UsdaTask).delete()
        db.query(TranslationConfig).delete()
        db.query(UsdaFoodNutrient).delete()
        db.query(UsdaFood).delete()
        db.commit()
    finally:
        db.close()


class NonAdminFakeUser:
    """非管理员测试用户（id=2）。"""
    id = 2
    username = "normal"
    email = "n@b.c"
    phone = None
    is_admin = False
    is_active = True
    email_verified = True
    token_version = 0
    created_at = None


def _fake_non_admin_user():
    return NonAdminFakeUser()


@pytest.fixture()
def as_admin():
    """以管理员身份请求（override get_current_user 为 FakeUser）。"""
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = fake_current_user
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest.fixture()
def as_non_admin():
    """以普通用户身份请求（override get_current_user 为 NonAdminFakeUser）。"""
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = _fake_non_admin_user
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
