"""
File: app/db/models/insights_report_qa.py
Description: 洞察报告问答记录表 (QA Pair)

对应前端 "洞察报告" 的 AI 对话功能。
主键名统一使用 'id'。

Author: jinmozhe
Created: 2026-02-08
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

# 1. 直接引用底层 Base
from app.db.models.base import Base


class InsightsReportQA(Base):
    """
    洞察报告问答记录表
    """

    __tablename__ = "insights_report_qa"

    # ========================================
    # 1. 字段定义
    # ========================================

    # --- 主键 (统一使用 id) ---
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
        comment="问答对ID (UUID v7)",
    )

    # --- 归属信息 ---
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="关联的洞察报告ID",
    )

    user_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="用户ID",
    )

    marketplace_id: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="市场ID",
    )

    # --- 问答内容 ---
    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="用户提问内容",
    )

    thought_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="AI思考过程 (CoT内容)",
    )

    answer: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="AI最终回答 (Markdown)",
    )

    # STANDARD2026: 移除 Python default, 依赖 server_default 或 Service 层传入
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'PENDING'"),
        comment="状态: PENDING, GENERATING, COMPLETED, FAILED",
    )

    # --- 审计字段 ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间 (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间 (UTC)",
    )

    # ========================================
    # 2. 数据库级约束与索引
    # ========================================
    __table_args__ = (
        # ----- Constraints (Fail Fast) -----
        CheckConstraint(
            "status IN ('PENDING', 'GENERATING', 'COMPLETED', 'FAILED')",
            name="ck_ins_qa_status_valid",
        ),
        CheckConstraint("length(trim(user_id)) > 0", name="ck_ins_qa_user_valid"),
        CheckConstraint(
            "length(trim(marketplace_id)) > 0", name="ck_ins_qa_market_valid"
        ),
        CheckConstraint("length(trim(question)) > 0", name="ck_ins_qa_question_valid"),
        # ----- Indexes -----
        # 优化按报告ID的时间轴查询 (Chat History)
        Index(
            "ix_ins_qa_report_timeline",
            "report_id",
            "created_at",
        ),
        {"comment": "洞察报告问答表 - 存储基于洞察报告的多轮对话记录"},
    )
