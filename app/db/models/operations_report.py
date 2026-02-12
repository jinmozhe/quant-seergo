"""
File: app/db/models/operations_report.py
Description: 运营领域聚合数据模型

本文件包含 Operations 领域的所有核心实体：
1. OperationsReport: 主表 (聚合根, 存储KPI/诊断看板/RAG上下文)
2. OperationsChangeLog: 子表 (三维变化明细, 基于时间窗口查询)
3. OperationsAuditLog: 子表 (操作审计日志, 基于时间窗口查询)
4. OperationsReportQA: 子表 (智能问答记录, 关联具体报告)

Author: jinmozhe
Created: 2026-02-12
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from app.db.models.base import Base


class OperationsReport(Base):
    """
    [Root Entity] 运营报告主表
    只存储核心维度、KPI、全域诊断看板(聚合数据)及 RAG 上下文。
    """

    __tablename__ = "operations_report"

    # ========================================
    # 1. 字段定义
    # ========================================

    # --- 主键 ---
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
        comment="主键 (UUID v7)",
    )

    # --- 归属信息 ---
    user_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="用户ID (业务必填)",
    )

    marketplace_id: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="市场ID (业务必填)",
    )

    # --- 报告周期 ---
    period_start: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="报告周期开始日期",
    )

    period_end: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="报告周期结束日期",
    )

    week: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="第几周",
    )

    # --- 业务分类 ---
    ad_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="广告类型",
    )

    report_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="报告类型",
    )

    report_source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="报告来源",
    )

    # --- 核心数据 (聚合/上下文) ---
    # Hero 核心概览数据
    hero: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="核心概览指标 (JSON对象)",
    )

    # [RAG Context]
    mcp_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="RAG上下文数据 (JSON对象)",
    )

    # [KPI] 关键绩效指标
    kpi: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="关键绩效指标数据 (JSON对象)",
    )

    # [Diagnosis] 全域诊断看板
    diagnosis: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="全域诊断数据 (JSON对象)",
    )

    # --- 文件 ---
    pdf_path: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="报告PDF下载路径",
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
    # 2. 约束与索引
    # ========================================
    __table_args__ = (
        # Check Constraints
        CheckConstraint("length(trim(user_id)) > 0", name="ck_ops_report_user_valid"),
        CheckConstraint(
            "length(trim(marketplace_id)) > 0", name="ck_ops_report_market_valid"
        ),
        CheckConstraint(
            "period_end >= period_start", name="ck_ops_report_period_logic"
        ),
        # JSON Constraints
        CheckConstraint(
            "jsonb_typeof(mcp_data) = 'object'", name="ck_ops_report_mcp_data_object"
        ),
        # [NEW] 增加类型约束
        CheckConstraint(
            "jsonb_typeof(hero) = 'object'", name="ck_ops_report_hero_object"
        ),
        CheckConstraint(
            "jsonb_typeof(kpi) = 'object'", name="ck_ops_report_kpi_object"
        ),
        CheckConstraint(
            "jsonb_typeof(diagnosis) = 'object'", name="ck_ops_report_diagnosis_object"
        ),
        # Unique & Index
        UniqueConstraint(
            "user_id",
            "marketplace_id",
            "period_start",
            "period_end",
            "ad_type",
            "report_type",
            "report_source",
            name="uq_ops_report_full_identity",
        ),
        Index(
            "ix_ops_report_lookup",
            "user_id",
            "marketplace_id",
            "period_start",
            "ad_type",
        ),
        {"comment": "运营报告主表 - 存储KPI及诊断看板"},
    )


class OperationsChangeLog(Base):
    """
    [Child Entity] 三维变化记录表 (独立流水)
    查询: WHERE user_id=? AND market=? AND period_start=? AND period_end=? AND category=?
    """

    __tablename__ = "operations_change_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
        comment="记录ID (UUID v7)",
    )

    # --- 查询维度 ---
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, comment="用户ID")

    marketplace_id: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="市场ID"
    )

    # [Redundant Fields] 冗余报告周期，便于直接查询
    period_start: Mapped[date] = mapped_column(
        Date, nullable=False, comment="报告周期开始日期"
    )

    period_end: Mapped[date] = mapped_column(
        Date, nullable=False, comment="报告周期结束日期"
    )

    # 类型 (开放录入): risk, opportunity, cyclical-neg, cyclical-pos, environment 等
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="变化分类"
    )

    # 内容: 前端展示所需的完整 JSON
    content: Mapped[dict] = mapped_column(
        JSONB, nullable=False, comment="变化详情 (JSON)"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="记录时间 (UTC)",
    )

    __table_args__ = (
        # [UPDATED] 开放录入，仅校验非空
        CheckConstraint(
            "length(trim(category)) > 0", name="ck_ops_change_category_not_empty"
        ),
        CheckConstraint(
            "period_end >= period_start", name="ck_ops_change_period_logic"
        ),
        CheckConstraint(
            "jsonb_typeof(content) = 'object'", name="ck_ops_change_content_object"
        ),
        # 复合索引优化
        Index(
            "ix_ops_change_query",
            "user_id",
            "marketplace_id",
            "period_start",
            "period_end",
            "category",
            "created_at",
        ),
        {"comment": "运营三维变化明细表"},
    )


class OperationsAuditLog(Base):
    """
    [Child Entity] 操作审计日志表 (独立流水)
    查询: WHERE user_id=? AND market=? AND period_start=? AND period_end=? AND category=?
    """

    __tablename__ = "operations_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
        comment="日志ID (UUID v7)",
    )

    # --- 查询维度 ---
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, comment="用户ID")

    marketplace_id: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="市场ID"
    )

    # [Redundant Fields] 冗余报告周期
    period_start: Mapped[date] = mapped_column(
        Date, nullable=False, comment="报告周期开始日期"
    )

    period_end: Mapped[date] = mapped_column(
        Date, nullable=False, comment="报告周期结束日期"
    )

    # 类型 (开放录入): executed, pending, skipped, failed 等
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="审计状态分类"
    )

    # 内容
    content: Mapped[dict] = mapped_column(
        JSONB, nullable=False, comment="日志详情 (JSON)"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="日志时间 (UTC)",
    )

    __table_args__ = (
        # [UPDATED] 开放录入，仅校验非空
        CheckConstraint(
            "length(trim(category)) > 0", name="ck_ops_audit_category_not_empty"
        ),
        CheckConstraint("period_end >= period_start", name="ck_ops_audit_period_logic"),
        CheckConstraint(
            "jsonb_typeof(content) = 'object'", name="ck_ops_audit_content_object"
        ),
        # 复合索引优化
        Index(
            "ix_ops_audit_query",
            "user_id",
            "marketplace_id",
            "period_start",
            "period_end",
            "category",
            "created_at",
        ),
        {"comment": "运营操作审计日志表"},
    )


class OperationsReportQA(Base):
    """
    [Child Entity] 运营报告问答记录表
    查询: 基于 report_id 关联具体报告的 Context (mcp_data)
    """

    __tablename__ = "operations_report_qa"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
        comment="问答对ID (UUID v7)",
    )

    # --- 归属信息 (强关联) ---
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operations_report.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联的运营报告ID",
    )

    user_id: Mapped[str] = mapped_column(String(50), nullable=False, comment="用户ID")

    marketplace_id: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="市场ID"
    )

    # --- 问答内容 ---
    question: Mapped[str] = mapped_column(Text, nullable=False, comment="用户提问内容")

    thought_content: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="AI思考过程 (CoT)"
    )

    answer: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="AI最终回答 (Markdown)"
    )

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

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'GENERATING', 'COMPLETED', 'FAILED')",
            name="ck_ops_qa_status_valid",
        ),
        CheckConstraint("length(trim(user_id)) > 0", name="ck_ops_qa_user_valid"),
        CheckConstraint(
            "length(trim(marketplace_id)) > 0", name="ck_ops_qa_market_valid"
        ),
        CheckConstraint("length(trim(question)) > 0", name="ck_ops_qa_question_valid"),
        # 索引优化: 聊天记录通常按时间轴展示
        Index(
            "ix_ops_qa_timeline",
            "report_id",
            "created_at",
        ),
        {"comment": "运营报告智能问答记录表"},
    )
