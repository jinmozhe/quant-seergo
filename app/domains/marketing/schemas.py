"""
File: app/domains/marketing/schemas.py
Description: 营销领域 Pydantic 模型 (精简演示版)
"""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ------------------------------------------------------------------------------
# 1. 请求模型
# ------------------------------------------------------------------------------
class ReportListRequest(BaseModel):
    """
    查询列表的请求参数
    """

    user_id: str = Field(..., description="用户ID")
    marketplace_id: str = Field(..., description="市场ID")


# ------------------------------------------------------------------------------
# 2. 响应模型 (精简列表项)
# ------------------------------------------------------------------------------
class MarketingReportItem(BaseModel):
    """
    营销报告单项数据。
    [Change] 移除了 mcp_data，只保留元数据和下载链接。
    """

    # 基础信息
    id: UUID = Field(..., description="报告ID (UUID v7)")

    # 周期
    period_start: date = Field(..., description="开始日期")
    period_end: date = Field(..., description="结束日期")

    # 类型与来源
    report_type: str = Field(..., description="报告类型")
    report_source: str = Field(..., description="报告来源")

    # 下载路径
    pdf_path: str | None = Field(default=None, description="PDF文件路径")

    model_config = ConfigDict(from_attributes=True)
