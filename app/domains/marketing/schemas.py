"""
File: app/domains/marketing/schemas.py
Description: 营销领域 Pydantic 模型 (扁平演示版)
"""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ------------------------------------------------------------------------------
# 1. 请求模型 (POST Body)
# ------------------------------------------------------------------------------
class ReportListRequest(BaseModel):
    """
    查询列表的请求参数
    """

    user_id: str = Field(..., description="用户ID")
    marketplace_id: str = Field(..., description="市场ID")


# ------------------------------------------------------------------------------
# 2. 响应模型 (扁平列表项)
# ------------------------------------------------------------------------------
class MarketingReportItem(BaseModel):
    """
    营销报告单项数据 (扁平结构)
    直接对应数据库的一行记录。
    """

    # 基础信息
    id: UUID = Field(..., description="报告ID (UUID v7)")

    # 周期
    period_start: date = Field(..., description="开始日期")
    period_end: date = Field(..., description="结束日期")

    # 类型与来源
    report_type: str = Field(..., description="报告类型")
    report_source: str = Field(..., description="报告来源")

    # 核心数据
    mcp_data: dict = Field(..., description="核心指标数据")

    # 下载路径
    pdf_path: str | None = Field(default=None, description="PDF文件路径")

    model_config = ConfigDict(from_attributes=True)
