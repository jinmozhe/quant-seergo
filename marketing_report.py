import uuid
from datetime import date, datetime
from sqlalchemy import String, Date, DateTime, text, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.settings.database import Base

class MarketingReport(Base):
    """营销报告表 (MarketingReport)
    
    对应前端 "下载分析报告" 功能。
    单次交互仅下载一条特定周期的报告记录。
    
    设计原则:
    1. 归属明确: 必须包含 user_id 和 marketplace_id，且不可为空。
    2. 唯一性: (user, market, period, type, source) 构成业务上的唯一键。
    
    枚举映射:
    ----------------
    report_type: DIAGNOSTIC, EFFECT
    report_source: COMPREHENSIVE, SP_ASIN, SP_KEYWORD, SB_ASIN, SB_VIDEO, SB_KEYWORD, SD_AUDIENCE, SD_OTHER
    """
    
    __tablename__ = "marketing_report"
    
    # ========================================
    # 主键
    # ========================================
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        comment='主键ID'
    )
    
    # ========================================
    # 归属信息 (User & Market)
    # ========================================
    
    user_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment='用户ID (业务必填)'
    )

    marketplace_id: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment='市场ID (业务必填)'
    )

    # ========================================
    # 报告周期 (UI: 01/22 - 01/28)
    # ========================================

    period_start: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment='报告周期开始日期'
    )
    
    period_end: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment='报告周期结束日期'
    )

    # ========================================
    # 业务分类
    # ========================================

    report_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment='报告类型: DIAGNOSTIC, EFFECT'
    )
    
    report_source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment='报告来源: COMPREHENSIVE, SP_ASIN, etc.'
    )

    # ========================================
    # 核心数据
    # ========================================

    mcp_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment='MCP 报告核心数据 (JSON对象)'
    )

    # ========================================
    # 系统时间 (数据库生成)
    # ========================================
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
        comment='生成时间 (UTC)'
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
        comment='更新时间 (UTC)'
    )
    
    # ========================================
    # 约束与索引
    # ========================================
    
    __table_args__ = (
        # ===== 完整性约束 (Constraints) =====
        
        # 1. 基础字段非空校验 (Trim后长度大于0)
        CheckConstraint("length(trim(user_id)) > 0", name='ck_mk_report_user_valid'),
        CheckConstraint("length(trim(marketplace_id)) > 0", name='ck_mk_report_market_valid'),
        
        # 2. 时间逻辑校验 (结束时间 >= 开始时间)
        CheckConstraint('period_end >= period_start', name='ck_mk_report_period_logic'),
        
        # 3. 枚举校验
        CheckConstraint(
            "report_type IN ('DIAGNOSTIC', 'EFFECT')", 
            name='ck_mk_report_type_valid'
        ),
        CheckConstraint(
            "report_source IN ('COMPREHENSIVE', 'SP_ASIN', 'SP_KEYWORD', 'SB_ASIN', 'SB_VIDEO', 'SB_KEYWORD', 'SD_AUDIENCE', 'SD_OTHER')", 
            name='ck_mk_report_source_valid'
        ),
        
        # 4. JSON 结构校验 (确保是 Object 而不是 Array 或 null)
        CheckConstraint("jsonb_typeof(mcp_data) = 'object'", name='ck_mk_report_mcp_object'),

        # ===== 索引与唯一性 (Indexes) =====
        
        # 1. 严格业务唯一键: 
        # 锁定 "某用户-某市场-某时段-某类型-某来源" 只能有一份报告。
        UniqueConstraint(
            'user_id', 
            'marketplace_id', 
            'period_start', 
            'period_end', 
            'report_type', 
            'report_source', 
            name='uq_mk_report_full_identity'
        ),
        
        # 2. 查找索引:
        # 场景：前端查询历史报告列表
        Index('ix_mk_report_lookup', 'user_id', 'marketplace_id', 'period_start', 'report_type'),
        
        {'comment': '营销报告表 - 存储用户维度的广告周期性诊断数据'}
    )