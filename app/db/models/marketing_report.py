"""
File: app/db/models/marketing_report.py
Description: 营销分析报告模型

对应前端 "下载分析报告" 功能。
变更：
1. 新增 ad_type 字段
2. report_type / report_source 改为开放式录入 (移除 Enum 约束，改为非空约束)

Author: jinmozhe
Created: 2026-02-03
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


class MarketingReport(Base):
    """
    营销报告表
    """

    __tablename__ = "marketing_report"

    # ========================================
    # 1. 字段定义 (Columns Definitions)
    # ========================================

    # --- 主键 (统一使用 id) ---
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

    # --- 业务分类 (开放式录入) ---
    # 新增字段: 广告类型
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

    # --- 核心数据与文件 ---
    mcp_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="MCP 报告核心数据 (JSON对象)",
    )

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
        # 基础字段非空校验
        CheckConstraint("length(trim(user_id)) > 0", name="ck_mk_report_user_valid"),
        CheckConstraint(
            "length(trim(marketplace_id)) > 0", name="ck_mk_report_market_valid"
        ),
        # 周期逻辑校验
        CheckConstraint("period_end >= period_start", name="ck_mk_report_period_logic"),
        # 业务分类非空校验 (替代原 Enum 约束)
        # STANDARD2026 3.6.1: 即使是开放录入，必填字段也禁止存入空字符串或纯空格
        CheckConstraint(
            "length(trim(ad_type)) > 0", name="ck_mk_report_ad_type_not_empty"
        ),
        CheckConstraint(
            "length(trim(report_type)) > 0", name="ck_mk_report_type_not_empty"
        ),
        CheckConstraint(
            "length(trim(report_source)) > 0", name="ck_mk_report_source_not_empty"
        ),
        # 数据结构校验
        CheckConstraint(
            "jsonb_typeof(mcp_data) = 'object'", name="ck_mk_report_mcp_object"
        ),
        CheckConstraint(
            "pdf_path IS NULL OR length(trim(pdf_path)) > 0",
            name="ck_mk_report_pdf_path_valid",
        ),
        # ----- Unique & Indexes -----
        UniqueConstraint(
            "user_id",
            "marketplace_id",
            "period_start",
            "period_end",
            "ad_type",  # 加入联合唯一索引
            "report_type",
            "report_source",
            name="uq_mk_report_full_identity",
        ),
        Index(
            "ix_mk_report_lookup",
            "user_id",
            "marketplace_id",
            "period_start",
            "ad_type",  # 加入常用查询索引
            "report_type",
        ),
        {"comment": "营销报告表 - 存储用户维度的广告周期性诊断数据"},
    )
