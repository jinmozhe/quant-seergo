"""
File: tests/conftest.py
Description: Pytest 全局 Fixtures 配置 (Async + 独立测试库)

修正说明：
1. 移除了手动定义的 event_loop fixture (交给 pytest-asyncio 自动管理)
2. 保留了 Windows 平台的 SelectorEventLoopPolicy 补丁
3. 依赖 pyproject.toml 中的 asyncio_default_fixture_loop_scope = "session"

Author: jinmozhe
Created: 2025-11-26
"""

import asyncio
import sys
from collections.abc import AsyncGenerator

# ------------------------------------------------------------------------------
# Windows 平台特定修复 (必须在任何 async 操作之前)
# ------------------------------------------------------------------------------
if sys.platform == "win32":
    # 强制使用 WindowsSelectorEventLoopPolicy 以解决 asyncpg 在 Windows 下的兼容性问题
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.deps import get_db
from app.core.config import settings
from app.db.models import Base
from app.main import app

# ------------------------------------------------------------------------------
# 1. 环境配置覆写
# ------------------------------------------------------------------------------

TEST_DB_NAME = "fastapi_test"

original_uri = settings.SQLALCHEMY_DATABASE_URI
if original_uri:
    from sqlalchemy.engine.url import make_url

    url = make_url(original_uri)
    test_url = url.set(database=TEST_DB_NAME)
    settings.SQLALCHEMY_DATABASE_URI = str(test_url)


# ------------------------------------------------------------------------------
# 2. 全局 Fixtures
# ------------------------------------------------------------------------------

# 注意：已移除 event_loop fixture，由 pytest-asyncio 根据 pyproject.toml 配置自动管理


@pytest_asyncio.fixture(scope="session")
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """
    创建测试专用的数据库引擎 (Session 级别)。
    """
    engine = create_async_engine(
        str(settings.SQLALCHEMY_DATABASE_URI),
        echo=False,
        pool_pre_ping=True,
    )

    # 1. 测试开始前：重置 Schema
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # 2. 测试结束后：清理
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    获取测试用的数据库会话 (Function 级别)。
    """
    async_session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with async_session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    获取异步 HTTP 客户端。
    """

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"  # type: ignore
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
