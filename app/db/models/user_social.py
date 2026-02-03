"""
File: app/db/models/user_social.py
Description: 用户三方绑定模型 (微信/Google等)

本表用于存储多渠道的三方登录凭证。
一个 User 可以对应多个 Social 记录 (如同时绑定微信小程序和公众号)。

注意：
采用 "No-Relationship" 模式，不显式定义 ORM relationship。
User 与 UserSocial 的关联仅通过 user_id 外键物理约束。
严禁使用物理级联删除，以配合系统的软删除策略。

Author: jinmozhe
Created: 2025-12-02
"""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.db.models.base import UUIDModel


class UserSocial(UUIDModel):
    """
    用户三方绑定表 (N:1 User)
    """

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return "user_socials"

    # --------------------------------------------------------------------------
    # 外键关联
    # --------------------------------------------------------------------------

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        # 物理外键约束，保证数据完整性
        # ❌ 严禁 ondelete="CASCADE"：用户仅软删除，绑定关系必须保留
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="关联用户ID",
    )

    # --------------------------------------------------------------------------
    # 三方核心凭证
    # --------------------------------------------------------------------------

    # 平台标识: wechat_mini(小程序), wechat_mp(公众号), google, apple
    platform: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="平台标识"
    )

    # 三方唯一ID (OpenID / Sub)
    openid: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="三方唯一ID(OpenID)"
    )

    # 跨应用统一ID (微信 UnionID)
    unionid: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True, comment="微信UnionID"
    )

    # --------------------------------------------------------------------------
    # 扩展数据 (JSON)
    # --------------------------------------------------------------------------

    # 存储三方返回的原始数据快照
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, comment="三方原始数据快照"
    )
