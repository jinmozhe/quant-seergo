"""
File: app/db/models/user_profile.py
Description: 用户扩展资料模型 (实名认证/档案)

本表用于存储用户敏感信息 (PII) 和低频访问的档案数据。
为了数据安全与性能，与 User 核心表分离。

注意：
采用 "No-Relationship" 模式，不显式定义 ORM relationship。
User 与 UserProfile 的关联仅通过 user_id 外键物理约束。

Author: jinmozhe
Created: 2025-12-02
"""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.db.models.base import UUIDModel


class UserProfile(UUIDModel):
    """
    用户档案表 (1:1 User)
    """

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return "user_profiles"

    # --------------------------------------------------------------------------
    # 外键关联
    # --------------------------------------------------------------------------

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        # 物理外键约束，确保数据完整性
        # 不设置 ondelete="CASCADE"，防止物理删除用户时意外删除档案
        ForeignKey("users.id"),
        unique=True,  # 确保 1:1 关系
        nullable=False,
        comment="关联用户ID",
    )

    # --------------------------------------------------------------------------
    # 敏感实名信息 (加密存储)
    # --------------------------------------------------------------------------

    # 真实姓名 (密文)
    real_name_enc: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="真实姓名(密文)"
    )

    # 身份证号 (密文)
    identity_card_enc: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="身份证号(密文)"
    )

    # 身份证号哈希 (用于查重/精确查找)
    identity_card_hash: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True, comment="身份证号哈希(查重)"
    )

    # --------------------------------------------------------------------------
    # 身份证详情 (OCR 结果 / 明文)
    # --------------------------------------------------------------------------

    # 证件图片：仅存储 OSS 对象路径 (Key)
    id_card_front_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="身份证正面OSS路径"
    )

    id_card_back_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="身份证反面OSS路径"
    )

    # 签发机关
    authority: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="签发机关"
    )

    # 户籍地址 (OCR 完整字符串)
    address: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="户籍地址"
    )

    # 有效期：拆分为起始日和截止日
    # 截止日为 NULL 代表 "长期"
    id_card_valid_from: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="有效期起始"
    )

    id_card_valid_to: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="有效期截止(NULL=长期)"
    )

    # --------------------------------------------------------------------------
    # 基础档案
    # --------------------------------------------------------------------------

    # 性别: M=Male, F=Female, U=Unknown
    gender: Mapped[str | None] = mapped_column(
        String(10), nullable=True, comment="性别"
    )

    # 生日
    birthday: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="出生日期"
    )

    # 民族
    nation: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="民族"
    )

    # 个人简介
    bio: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="个人简介"
    )
