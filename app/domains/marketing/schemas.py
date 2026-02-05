"""
File: app/domains/marketing/schemas.py
Description: 营销领域 Pydantic 模型

包含：
1. 报告列表查询 (ReportListRequest, MarketingReportItem)
2. 智能问答交互 (ChatInitRequest, ChatInitResponse, ChatHistoryRequest, ChatRecordItem)

Author: jinmozhe
Created: 2026-02-03
Updated: 2026-02-04 (Add Chat History Schemas)
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ==============================================================================
# 1. 报告列表相关 (Existing)
# ==============================================================================


class ReportListRequest(BaseModel):
    """
    查询列表的请求参数
    """

    user_id: str = Field(..., description="用户ID")
    marketplace_id: str = Field(..., description="市场ID")


class MarketingReportItem(BaseModel):
    """
    营销报告单项数据 (精简版)
    """

    id: UUID = Field(..., description="报告ID (UUID v7)")
    period_start: date = Field(..., description="开始日期")
    period_end: date = Field(..., description="结束日期")
    report_type: str = Field(..., description="报告类型")
    report_source: str = Field(..., description="报告来源")
    pdf_path: str | None = Field(default=None, description="PDF文件路径")

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# 2. 智能问答相关 (RAG)
# ==============================================================================


class ChatInitRequest(BaseModel):
    """
    初始化对话请求。
    """

    user_id: str = Field(..., description="用户ID")
    marketplace_id: str = Field(..., description="市场ID")
    report_id: UUID = Field(..., description="关联的营销报告ID")
    question: str = Field(..., min_length=1, description="用户的问题")


class ChatInitResponse(BaseModel):
    """
    对话初始化响应。
    """

    qa_id: UUID = Field(..., description="生成的问答记录ID (UUID v7)")


# [New] 获取历史记录请求
class ChatHistoryRequest(BaseModel):
    """
    查询对话历史请求参数
    """

    user_id: str = Field(..., description="用户ID")
    marketplace_id: str = Field(..., description="市场ID")
    report_id: UUID = Field(..., description="关联的营销报告ID")


# [New] 历史记录单项
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
