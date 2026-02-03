"""
File: app/domains/users/service.py
Description: 用户领域服务 (业务逻辑层)

本模块封装用户管理的核心业务逻辑：
1. 用户注册 (创建)：校验唯一性、哈希密码、写入数据库。
2. 用户查询：通过 ID 获取用户 (自动过滤软删除)。
3. 用户更新：处理密码哈希、变更唯一性校验。
4. 异常处理：抛出业务特定的 AppException (配合 UserErrorCode)。

Author: jinmozhe
Created: 2025-11-25
Updated: 2026-02-02 (Fix ErrorCodes & Strict Mode)
"""

from uuid import UUID

from app.core.exceptions import AppException, NotFoundException
from app.core.logging import logger
from app.core.security import get_password_hash_async
from app.db.models.user import User
from app.domains.users.constants import UserErrorCode  # ✅ 新增依赖
from app.domains.users.repository import UserRepository
from app.domains.users.schemas import UserCreate, UserUpdate


class UserService:
    """
    用户领域服务。
    """

    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def create(self, obj_in: UserCreate) -> User:
        """
        创建新用户 (注册)。
        """
        # 1. 唯一性校验 (Fail Fast)
        if await self.repo.get_by_phone_number(obj_in.phone_number):
            # ✅ 修正：使用枚举，抛弃 code=40001
            raise AppException(UserErrorCode.PHONE_EXIST)

        if obj_in.email and await self.repo.get_by_email(obj_in.email):
            raise AppException(UserErrorCode.EMAIL_EXIST)

        if obj_in.username and await self.repo.get_by_username(obj_in.username):
            raise AppException(UserErrorCode.USERNAME_EXIST)

        # 2. 密码加密 (使用异步版本，避免阻塞事件循环)
        hashed_password = await get_password_hash_async(obj_in.password)

        # 3. 准备数据
        # 必须排除 password 明文，防止写入
        user_data = obj_in.model_dump(exclude={"password"}, exclude_unset=True)
        user = User(**user_data, hashed_password=hashed_password)

        # 4. 持久化与事务提交 (Service 层负责事务边界)
        self.repo.session.add(user)
        await self.repo.session.flush()
        await self.repo.session.commit()
        await self.repo.session.refresh(user)

        logger.bind(user_id=str(user.id)).info("User created successfully")

        return user

    async def get(self, user_id: UUID) -> User:
        """
        获取用户详情。
        如果用户不存在或已被软删除，抛出 NotFoundException。
        """
        user = await self.repo.get(user_id)

        # 业务层要把"软删除"视为"不存在"
        if not user or user.is_deleted:
            raise NotFoundException(
                message="用户不存在", data={"user_id": str(user_id)}
            )
        return user

    async def update(self, user_id: UUID, obj_in: UserUpdate) -> User:
        """
        更新用户信息 (支持密码修改和唯一性校验)。
        """
        user = await self.get(user_id)

        # 获取更新数据 (字典)
        update_data = obj_in.model_dump(exclude_unset=True)

        # 1. 处理密码修改 (特殊字段)
        new_password = update_data.pop("password", None)
        if new_password:
            hashed_password = await get_password_hash_async(new_password)
            user.hashed_password = hashed_password

        # 2. 处理唯一性字段变更 (防止冲突)
        # 逻辑：如果字段存在于更新数据中，且值发生了变化，则检查数据库是否已存在该值

        if (
            "phone_number" in update_data
            and update_data["phone_number"] != user.phone_number
        ):
            existing = await self.repo.get_by_phone_number(update_data["phone_number"])
            if existing and existing.id != user.id:
                raise AppException(UserErrorCode.PHONE_EXIST)

        if "email" in update_data and update_data["email"] != user.email:
            # Email 可能是 None，如果不是 None 再查重
            if update_data["email"] is not None:
                existing = await self.repo.get_by_email(update_data["email"])
                if existing and existing.id != user.id:
                    raise AppException(UserErrorCode.EMAIL_EXIST)

        if "username" in update_data and update_data["username"] != user.username:
            if update_data["username"] is not None:
                existing = await self.repo.get_by_username(update_data["username"])
                if existing and existing.id != user.id:
                    raise AppException(UserErrorCode.USERNAME_EXIST)

        # 3. 执行常规字段更新
        # 注意：这里 update 方法应该只更新 update_data 中的字段
        updated_user = await self.repo.update(user, update_data)

        # 4. 提交事务
        await self.repo.session.commit()
        await self.repo.session.refresh(updated_user)

        logger.bind(user_id=str(user_id)).info("User updated successfully")

        return updated_user
