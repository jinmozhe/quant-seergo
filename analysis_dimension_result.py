import uuid
from datetime import date, datetime
from sqlalchemy import String, Date, DateTime, text, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.settings.database import Base

class AnalysisDimensionResult(Base):
    """多维度分析结果表 (AnalysisDimensionResult)
    
    存储用户在特定周期下的不同业务模块的细分分析数据。
    设计为“原子化”存储，每个维度一条记录，便于前端按需加载和独立更新。
    
    枚举映射 (dimension_type):
    ----------------------------------------------------------
    - KPI_METRICS:          关于 KPI 的各种核心指标数据
    - ANALYST_INSIGHTS:     首席分析师结论与建议
    - COVERAGE_PRECISION:   覆盖度与精准度分析
    - AI_REVENUE_SIMULATION: AI 优化收益推演
    - DECISION_CENTER:      智能决策控制中心数据
    ----------------------------------------------------------
    """
    
    __tablename__ = "analysis_dimension_result"
    
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
    # 归属信息
    # ========================================
    
    user_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment='用户ID'
    )

    marketplace_id: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment='市场ID'
    )

    # ========================================
    # 周期信息 (Period)
    # ========================================

    period_start: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment='分析周期开始日期'
    )
    
    period_end: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment='分析周期结束日期'
    )

    # ========================================
    # 维度与数据
    # ========================================

    dimension_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment='维度类型: KPI_METRICS, ANALYST_INSIGHTS, etc.'
    )
    
    data_payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment='该维度的具体分析数据 (JSON对象)'
    )

    # ========================================
    # 系统时间
    # ========================================
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
        comment='创建时间 (UTC)'
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        onupdate=text("now()"),
        nullable=False,
        comment='更新时间 (UTC)'
    )
    
    # ========================================
    # 约束与索引
    # ========================================
    
    __table_args__ = (
        # ===== 完整性约束 (Constraints) =====
        
        # 1. 维度枚举校验 (严格限制 5 种类型)
        CheckConstraint(
            "dimension_type IN ('KPI_METRICS', 'ANALYST_INSIGHTS', 'COVERAGE_PRECISION', 'AI_REVENUE_SIMULATION', 'DECISION_CENTER')", 
            name='ck_ana_dim_type_valid'
        ),
        
        # 2. 基础字段非空校验
        CheckConstraint("length(trim(user_id)) > 0", name='ck_ana_dim_user_valid'),
        CheckConstraint("length(trim(marketplace_id)) > 0", name='ck_ana_dim_market_valid'),
        
        # 3. 时间逻辑校验
        CheckConstraint('period_end >= period_start', name='ck_ana_dim_period_logic'),
        
        # 4. JSON 结构校验
        CheckConstraint("jsonb_typeof(data_payload) = 'object'", name='ck_ana_dim_payload_object'),

        # ===== 索引与唯一性 (Indexes) =====
        
        # 1. 业务唯一键: 
        # 确保 "某用户-某市场-某周期" 下的 "某维度" 数据是唯一的。
        UniqueConstraint(
            'user_id', 
            'marketplace_id', 
            'period_start', 
            'period_end', 
            'dimension_type', 
            name='uq_ana_dim_identity'
        ),
        
        # 2. 核心查询索引:
        # 场景：一次性拉取某用户某周期的所有维度数据
        # SELECT * FROM analysis_dimension_result WHERE user_id=? AND period_start=?
        Index('ix_ana_dim_lookup', 'user_id', 'marketplace_id', 'period_start', 'period_end'),
        
        {'comment': '多维度分析结果表 - 存储拆分后的各个业务模块分析数据'}
    )