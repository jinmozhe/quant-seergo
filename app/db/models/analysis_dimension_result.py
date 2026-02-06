"""
File: app/db/models/analysis_dimension_result.py
Description: 多维度分析结果表，增加 SYSTEM 角色支持。

遵循 STANDARD2026.md 规范：
1. 强制使用 UUID v7。
2. 强制数据库级 CheckConstraint。
3. 强制 DateTime(timezone=True)。
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

from app.db.models.base import Base


class AnalysisDimensionResult(Base):
    """
    多维度分析结果表
    """

    __tablename__ = "analysis_dimension_result"

    # ========================================
    # 1. 字段定义
    # ========================================

    # --- 主键 (统一使用 id, UUID v7) ---
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
        comment="用户ID",
    )

    marketplace_id: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="市场ID",
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="目标角色: BOSS, ANALYST, OPS, SYSTEM",
    )

    # --- 周期信息 ---
    period_start: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="分析周期开始日期",
    )

    period_end: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="分析周期结束日期",
    )

    # --- 维度与数据 ---
    dimension_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="维度类型: KPI_METRICS, ANALYST_INSIGHTS, etc.",
    )

    data_payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="该维度的具体分析数据 (JSON对象)",
    )

    # --- 审计字段 (遵循 2026 强制时区规范) ---
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
        # ----- Constraints (Strict Mode) -----
        CheckConstraint(
            "dimension_type IN ('REPORT_HERO','KPI_METRICS', 'ANALYST_INSIGHTS', 'COVERAGE_PRECISION', 'AI_REVENUE_SIMULATION', 'DECISION_CENTER', 'FINAL_CTA')",
            name="ck_ana_dim_type_valid",
        ),
        # 核心修改点：增加 SYSTEM 约束
        CheckConstraint(
            "role IN ('BOSS', 'ANALYST', 'OPS', 'SYSTEM')",
            name="ck_ana_dim_role_valid",
        ),
        CheckConstraint("length(trim(user_id)) > 0", name="ck_ana_dim_user_valid"),
        CheckConstraint(
            "length(trim(marketplace_id)) > 0", name="ck_ana_dim_market_valid"
        ),
        CheckConstraint("period_end >= period_start", name="ck_ana_dim_period_logic"),
        CheckConstraint(
            "jsonb_typeof(data_payload) = 'object'",
            name="ck_ana_dim_payload_object",
        ),
        # ----- Unique & Indexes -----
        UniqueConstraint(
            "user_id",
            "marketplace_id",
            "role",
            "period_start",
            "period_end",
            "dimension_type",
            name="uq_ana_dim_identity",
        ),
        Index(
            "ix_ana_dim_lookup",
            "user_id",
            "marketplace_id",
            "role",
            "period_start",
            "period_end",
        ),
        {"comment": "多维度分析结果表 - 存储拆分后的各个业务模块分析数据"},
    )
