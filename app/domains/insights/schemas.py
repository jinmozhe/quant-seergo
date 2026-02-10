"""
File: app/domains/insights/schemas.py
Description: 洞察领域 Pydantic 模型

包含：
1. 报告列表查询 (InsightsReportItem - 精简版)
2. 最新报告详情查询 (LatestReportResponse - 含 ID 和 大字段)
3. 智能问答交互 (ChatInitRequest, ChatRecordItem)

Author: jinmozhe
Created: 2026-02-08
Updated: 2026-02-09
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


class InsightsReportItem(BaseModel):
    """
    洞察报告单项数据 (精简版)
    注意：列表页不返回 kpi/insights/ai 大字段，仅返回元数据
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
# 2. 最新报告详情查询 [New]
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
    包含 ID 和大字段 (kpi, insights, ai)
    """

    id: UUID = Field(..., description="报告ID")  # 补回 ID 字段
    period_start: date = Field(..., description="开始日期")
    period_end: date = Field(..., description="结束日期")

    ad_type: str = Field(..., description="广告类型")
    report_type: str = Field(..., description="报告类型")
    report_source: str = Field(..., description="报告来源")

    # JSONB 字段映射为 dict
    kpi: dict[str, Any] = Field(..., description="KPI 数据")
    insights: dict[str, Any] = Field(..., description="洞察结论")
    ai: dict[str, Any] = Field(..., description="AI 分析建议")

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# 3. 智能问答相关 (RAG)
# ==============================================================================


class ChatInitRequest(BaseModel):
    """
    初始化对话请求。
    """

    user_id: str = Field(..., description="用户ID")
    marketplace_id: str = Field(..., description="市场ID")
    report_id: UUID = Field(..., description="关联的洞察报告ID")
    question: str = Field(..., min_length=1, description="用户的问题")


class ChatInitResponse(BaseModel):
    """
    对话初始化响应。
    """

    qa_id: UUID = Field(..., description="生成的问答记录ID (UUID v7)")


class ChatHistoryRequest(BaseModel):
    """
    查询对话历史请求参数
    """

    user_id: str = Field(..., description="用户ID")
    marketplace_id: str = Field(..., description="市场ID")
    report_id: UUID = Field(..., description="关联的洞察报告ID")


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
