"""
File: app/domains/analysis/router.py
Description: 分析结果 HTTP 接口 (POST 模式 + 空状态支持)
Updated: 2026-02-04 (Support nullable response)
"""

from typing import Any

from fastapi import APIRouter

from app.core.response import ResponseModel
from app.domains.analysis.dependencies import AnalysisServiceDep
from app.domains.analysis.schemas import AnalysisLatestQuery

router = APIRouter(tags=["analysis"])


@router.post(
    "/latest",
    # 变更：泛型声明允许为 None
    response_model=ResponseModel[dict[str, Any] | None],
    summary="获取指定维度的最新分析数据",
)
async def get_latest_analysis_payload(
    service: AnalysisServiceDep,
    query: AnalysisLatestQuery,
) -> ResponseModel[dict[str, Any] | None]:
    """
    通过维度组合精准定位并返回最后一条 data_payload。

    - **Empty State**: 如果未找到数据，返回 200 OK 且 data 为 null。
    """
    data = await service.fetch_latest_payload(query)
    # 即使 data 是 None，ResponseModel.success 也能正确处理
    return ResponseModel.success(data=data)
