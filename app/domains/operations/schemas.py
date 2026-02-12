"""
File: app/domains/operations/schemas.py
Description: 运营领域 Pydantic 模型

包含：
1. 报告列表查询 (OperationsReportItem)
2. 最新报告详情查询 (LatestReportResponse - 含 KPI/Diagnosis)
3. 三维变化与审计日志分页查询 (ChangeLog/AuditLog)
4. 智能问答交互 (ChatInitRequest, ChatRecordItem)

Author: jinmozhe
Created: 2026-02-12
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ==============================================================================
# 1. 报告列表相关
# ==============================================================================


class ReportListRequest(BaseModel):
    """
    查询列表的请求参数
    """

    user_id: str = Field(..., description="用户ID")
    marketplace_id: str = Field(..., description="市场ID")


class OperationsReportItem(BaseModel):
    """
    运营报告单项数据 (精简版)
    用于列表页展示
    """

    id: UUID = Field(..., description="报告ID (UUID v7)")
    week: str = Field(..., description="第几周")
    ad_type: str = Field(..., description="广告类型")
    period_start: date = Field(..., description="开始日期")
    period_end: date = Field(..., description="结束日期")
    report_type: str = Field(..., description="报告类型")
    report_source: str = Field(..., description="报告来源")
    pdf_path: str | None = Field(default=None, description="PDF文件路径")

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# 2. 最新报告详情查询
# ==============================================================================


class LatestReportRequest(BaseModel):
    """
    获取最新报告详情请求参数
    """

    user_id: str = Field(..., description="用户ID")
    marketplace_id: str = Field(..., description="市场ID")
    ad_type: str = Field(..., description="广告类型 (如 ALL, SP, SB)")
    report_type: str = Field(..., description="报告类型 (如 DIAGNOSTIC)")
    report_source: str = Field(..., description="报告来源 (如 ALL)")


class LatestReportResponse(BaseModel):
    """
    最新报告详情响应
    包含: ID, 核心聚合数据 (KPI, Diagnosis)
    不包含: 大列表 (ChangeLog, AuditLog) -> 请使用独立接口分页获取
    """

    id: UUID = Field(..., description="报告ID")
    period_start: date = Field(..., description="开始日期")
    period_end: date = Field(..., description="结束日期")

    ad_type: str = Field(..., description="广告类型")
    report_type: str = Field(..., description="报告类型")
    report_source: str = Field(..., description="报告来源")

    # [Aggregation Data]
    hero: dict[str, Any] = Field(..., description="核心概览指标数据")
    kpi: dict[str, Any] = Field(..., description="关键绩效指标数据")
    diagnosis: dict[str, Any] = Field(..., description="全域诊断看板数据")

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# 3. 三维变化与审计日志 (分页查询)
# ==============================================================================


class BaseLogListRequest(BaseModel):
    """
    日志查询基类 (共享字段)
    """

    user_id: str = Field(..., description="用户ID")
    marketplace_id: str = Field(..., description="市场ID")
    period_start: date = Field(..., description="报告周期开始日期")
    period_end: date = Field(..., description="报告周期结束日期")
    category: str = Field(..., description="分类 (Risk, Executed...)")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=5, ge=1, le=100, description="每页条数")


# --- Change Log ---


class ChangeLogListRequest(BaseLogListRequest):
    """三维变化查询请求"""

    pass


class ChangeLogItem(BaseModel):
    """三维变化单项"""

    id: UUID = Field(..., description="记录ID")
    category: str = Field(..., description="分类")
    content: dict[str, Any] = Field(..., description="变化详情 (JSON)")
    created_at: datetime = Field(..., description="记录时间")

    model_config = ConfigDict(from_attributes=True)


class ChangeLogListResponse(BaseModel):
    """三维变化列表响应"""

    items: list[ChangeLogItem]
    total: int
    page: int
    page_size: int


# --- Audit Log ---


class AuditLogListRequest(BaseLogListRequest):
    """审计日志查询请求"""

    pass


class AuditLogItem(BaseModel):
    """审计日志单项"""

    id: UUID = Field(..., description="日志ID")
    category: str = Field(..., description="状态分类")
    content: dict[str, Any] = Field(..., description="日志详情 (JSON)")
    created_at: datetime = Field(..., description="日志时间")

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    """审计日志列表响应"""

    items: list[AuditLogItem]
    total: int
    page: int
    page_size: int


# ==============================================================================
# 4. 智能问答相关 (RAG)
# ==============================================================================


class ChatInitRequest(BaseModel):
    """
    初始化对话请求
    """

    user_id: str = Field(..., description="用户ID")
    marketplace_id: str = Field(..., description="市场ID")
    report_id: UUID = Field(..., description="关联的运营报告ID (用于获取 Context)")
    question: str = Field(..., min_length=1, description="用户的问题")


class ChatInitResponse(BaseModel):
    """
    对话初始化响应
    """

    qa_id: UUID = Field(..., description="生成的问答记录ID (UUID v7)")


class ChatHistoryRequest(BaseModel):
    """
    查询对话历史请求参数
    """

    user_id: str = Field(..., description="用户ID")
    marketplace_id: str = Field(..., description="市场ID")
    report_id: UUID = Field(..., description="关联的运营报告ID")


class ChatRecordItem(BaseModel):
    """
    问答记录详情
    """

    id: UUID = Field(..., description="记录ID")
    question: str = Field(..., description="用户提问")
    answer: str | None = Field(default=None, description="AI回答 (Markdown)")
    status: str = Field(..., description="状态: PENDING/GENERATING/COMPLETED/FAILED")
    created_at: datetime = Field(..., description="提问时间")

    model_config = ConfigDict(from_attributes=True)
