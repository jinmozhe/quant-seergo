"""
File: app/domains/analysis/schemas.py
Description: 分析结果领域的 Pydantic 模型

本模块定义了：
1. AnalysisLatestQuery: 用于 POST /latest 接口的请求体 Schema

Author: jinmozhe
Created: 2026-02-04
Updated: 2026-02-04 (Remove nested AnalysisPayloadRead)
"""

from pydantic import BaseModel, Field


class AnalysisLatestQuery(BaseModel):
    """
    查询最新分析结果的参数 (Request Body)
    """

    user_id: str = Field(..., description="用户ID")
    marketplace_id: str = Field(..., description="市场ID")
    role: str = Field(..., description="角色: BOSS, ANALYST, OPS, SYSTEM")
    dimension_type: str = Field(..., description="维度类型")
