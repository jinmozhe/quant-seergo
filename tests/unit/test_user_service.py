"""
File: tests/unit/test_user_service.py
Description: 用户领域服务单元测试

本模块测试 UserService 的核心业务逻辑：
1. 正常用户创建 (Happy Path)
2. 业务规则校验 (手机号/邮箱重复检测)
3. 密码哈希安全验证
4. 数据持久化验证

Author: jinmozhe
Created: 2025-11-26
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.security import verify_password
from app.db.models.user import User
from app.domains.users.repository import UserRepository
from app.domains.users.schemas import UserCreate
from app.domains.users.service import UserService

# ------------------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------------------


@pytest.fixture
def user_service(db_session: AsyncSession) -> UserService:
    """
    创建一个绑定了测试 Session 的 UserService 实例。

    说明：
    - db_session 来自 tests/conftest.py，已指向测试专用 PostgreSQL 数据库
    - 这里显式传入 User 模型，满足 BaseRepository 的泛型约束
    """
    repo = UserRepository(model=User, session=db_session)
    return UserService(repo=repo)


# ------------------------------------------------------------------------------
# Test Cases
# ------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_user_success(user_service: UserService) -> None:
    """测试：正常创建用户"""
    user_in = UserCreate(
        phone_number="+8613800000001",
        password="securepassword",
        username="testuser1",
        email="test1@example.com",
        full_name="Test User 1",
    )

    user = await user_service.create(user_in)

    # 1. 验证返回对象字段
    assert user.id is not None
    assert user.phone_number == user_in.phone_number
    assert user.email == user_in.email
    assert user.username == user_in.username

    # 2. 验证密码已加密 (不存储明文)
    assert user.hashed_password != user_in.password
    assert verify_password(user_in.password, user.hashed_password)

    # 3. 验证默认字段
    assert user.is_active is True
    assert user.is_superuser is False
    assert user.created_at is not None
    # 如果你的模型里有 updated_at 默认值，也可以一起断言：
    # assert user.updated_at is not None


@pytest.mark.asyncio
async def test_create_user_duplicate_phone(user_service: UserService) -> None:
    """测试：手机号重复注册应抛出异常"""
    # 1. 先创建一个用户
    user_in_1 = UserCreate(
        phone_number="+8613800000002",
        password="p1",
    )
    await user_service.create(user_in_1)

    # 2. 尝试用相同手机号创建第二个用户
    user_in_2 = UserCreate(
        phone_number="+8613800000002",  # 重复
        password="p2",
        username="othername",
    )

    # 3. 断言抛出 AppException
    with pytest.raises(AppException) as excinfo:
        await user_service.create(user_in_2)

    assert excinfo.value.code == 40001
    assert "手机号" in excinfo.value.message


@pytest.mark.asyncio
async def test_create_user_duplicate_email(user_service: UserService) -> None:
    """测试：邮箱重复注册应抛出异常"""
    # 1. 创建第一个用户
    user_in_1 = UserCreate(
        phone_number="+8613800000003",
        email="duplicate@example.com",
        password="p1",
    )
    await user_service.create(user_in_1)

    # 2. 创建第二个用户 (手机号不同，但邮箱相同)
    user_in_2 = UserCreate(
        phone_number="+8613800000004",
        email="duplicate@example.com",  # 重复
        password="p2",
    )

    with pytest.raises(AppException) as excinfo:
        await user_service.create(user_in_2)

    assert excinfo.value.code == 40002
    assert "邮箱" in excinfo.value.message
