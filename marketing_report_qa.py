import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, text, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from src.settings.database import Base

class MarketingReportQA(Base):
    """报告问答记录表 (MarketingReportQA)
    
    设计模式: Q&A Pair (一问一答)
    交互逻辑: 
    1. 列表加载: 按 report_id 筛选，按 created_at 正序 (ASC) 排列。
    2. 唯一性: id 是唯一主键。同一个 report_id 允许存在多条记录 (1:N)。
    
    状态流转:
    PENDING (排队中) -> GENERATING (生成中) -> COMPLETED (完成) / FAILED (失败)
    """
    
    __tablename__ = "marketing_report_qa"
    
    # ========================================
    # 主键
    # ========================================
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        comment='问答对ID'
    )
    
    # ========================================
    # 归属信息 (逻辑关联)
    # ========================================
    
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment='关联的营销报告ID'
    )
    
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
    # 问答内容
    # ========================================

    question: Mapped[str] = mapped_column(
        Text, 
        nullable=False,
        comment='用户提问内容'
    )
    
    # DeepSeek R1 等推理模型会先输出思考过程
    thought_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment='AI思考过程 (CoT内容)'
    )

    answer: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment='AI最终回答 (Markdown)'
    )
    
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'PENDING'"),
        comment='状态: PENDING, GENERATING, COMPLETED, FAILED'
    )

    # ========================================
    # 系统时间
    # ========================================
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
        comment='创建时间 (用于正序排列)'
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        onupdate=text("now()"),
        nullable=False,
        comment='更新时间'
    )
    
    # ========================================
    # 约束与索引
    # ========================================
    
    __table_args__ = (
        # ===== 完整性约束 (Constraints) =====
        
        # 1. 状态枚举校验
        CheckConstraint(
            "status IN ('PENDING', 'GENERATING', 'COMPLETED', 'FAILED')", 
            name='ck_mk_qa_status_valid'
        ),
        
        # 2. 基础字段非空校验 (Trim后长度大于0)
        CheckConstraint("length(trim(user_id)) > 0", name='ck_mk_qa_user_valid'),
        CheckConstraint("length(trim(marketplace_id)) > 0", name='ck_mk_qa_market_valid'),
        CheckConstraint("length(trim(question)) > 0", name='ck_mk_qa_question_valid'),

        # ===== 索引 (Indexes) =====
        
        # 核心查询索引:
        # 用于加载某个报告下的对话历史 (按时间正序)
        Index('ix_mk_qa_report_timeline', 'report_id', 'created_at'),
        
        {'comment': '报告分析问答表 - 存储基于报告的多轮对话记录'}
    )