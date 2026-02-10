"""
File: app/db/models/insights_report.py
Description: 洞察分析报告模型

对应前端 "下载洞察报告" 功能。
基于营销报告模型扩展，专注于 KPI、洞察结论与 AI 分析数据。

Author: jinmozhe
Created: 2026-02-08
Updated: 2025-XX-XX
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

# 1. 直接引用底层 Base
from app.db.models.base import Base


class InsightsReport(Base):
    """
    洞察报告表
    包含 KPI 指标、深度洞察及 AI 分析结论
    """

    __tablename__ = "insights_report"

    # ========================================
    # 1. 字段定义 (Columns Definitions)
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

    # [NEW] 新增字段: 周数
    # 仅用于前端展示和业务标记，不参与唯一性校验
    week: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="第几周 (开放录入)",
    )

    # --- 业务分类 (开放式录入) ---
    ad_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="广告类型 (开放录入)",
    )

    report_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="报告类型 (开放录入)",
    )

    report_source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="报告来源 (开放录入)",
    )

    # --- 核心数据 ---

    # [NEW] 新增字段: MCP 数据
    mcp_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="MCP 报告核心数据 (JSON对象)",
    )

    kpi: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="关键绩效指标数据 (JSON对象)",
    )

    insights: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="深度洞察结论 (JSON对象)",
    )

    ai: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="AI 分析与建议 (JSON对象)",
    )

    # --- 文件 ---
    pdf_path: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="报告PDF下载路径 (OSS/S3 Key)",
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
        # ----- Check Constraints (Fail Fast) -----
        CheckConstraint("length(trim(user_id)) > 0", name="ck_ins_report_user_valid"),
        CheckConstraint(
            "length(trim(marketplace_id)) > 0", name="ck_ins_report_market_valid"
        ),
        CheckConstraint(
            "period_end >= period_start", name="ck_ins_report_period_logic"
        ),
        # [UPDATE] 增加 week 的非空校验，但不加入唯一索引
        CheckConstraint("length(trim(week)) > 0", name="ck_ins_report_week_not_empty"),
        CheckConstraint(
            "length(trim(ad_type)) > 0", name="ck_ins_report_ad_type_not_empty"
        ),
        CheckConstraint(
            "length(trim(report_type)) > 0", name="ck_ins_report_type_not_empty"
        ),
        CheckConstraint(
            "length(trim(report_source)) > 0", name="ck_ins_report_source_not_empty"
        ),
        # [UPDATE] 增加 mcp_data 结构校验
        CheckConstraint(
            "jsonb_typeof(mcp_data) = 'object'", name="ck_ins_report_mcp_data_object"
        ),
        CheckConstraint(
            "jsonb_typeof(kpi) = 'object'", name="ck_ins_report_kpi_object"
        ),
        CheckConstraint(
            "jsonb_typeof(insights) = 'object'", name="ck_ins_report_insights_object"
        ),
        CheckConstraint("jsonb_typeof(ai) = 'object'", name="ck_ins_report_ai_object"),
        CheckConstraint(
            "pdf_path IS NULL OR length(trim(pdf_path)) > 0",
            name="ck_ins_report_pdf_path_valid",
        ),
        # ----- Unique & Indexes -----
        # [保持原样] 不包含 week，因为 period_start/end 已决定唯一性
        UniqueConstraint(
            "user_id",
            "marketplace_id",
            "period_start",
            "period_end",
            "ad_type",
            "report_type",
            "report_source",
            name="uq_ins_report_full_identity",
        ),
        # [保持原样] 不包含 week，利用 period_start 排序/筛选即可
        Index(
            "ix_ins_report_lookup",
            "user_id",
            "marketplace_id",
            "period_start",
            "ad_type",
            "report_type",
        ),
        {"comment": "洞察报告表 - 存储包含 KPI、洞察和 AI 建议的综合分析数据"},
    )
