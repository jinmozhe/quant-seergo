"""
File: app/domains/marketing/router.py
Description: 营销领域路由层

职责：
1. 声明 API 契约 (Endpoint, Method, Body)
2. 调用 Service
3. 封装统一响应 (ResponseModel)
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.deps import DBSession
from app.core.response import ResponseModel
from app.domains.marketing.repository import MarketingReportRepository
from app.domains.marketing.schemas import MarketingReportItem, ReportListRequest
from app.domains.marketing.service import MarketingReportService

router = APIRouter()


# ------------------------------------------------------------------------------
# Dependencies
# ------------------------------------------------------------------------------
async def get_marketing_service(session: DBSession) -> MarketingReportService:
    repo = MarketingReportRepository(model=None, session=session)  # type: ignore
    return MarketingReportService(repo)


MarketingServiceDep = Annotated[MarketingReportService, Depends(get_marketing_service)]

# ------------------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------------------


@router.post(
    "/reports/list",
    summary="获取报告列表 (Demo Lite)",
    description="传入 user_id 和 marketplace_id，返回精简版报告列表 (不含 mcp_data)。",
    response_model=ResponseModel[list[MarketingReportItem]],
)
async def get_report_list_demo(
    request: Request,
    req_data: ReportListRequest,
    service: MarketingServiceDep,
) -> ResponseModel[list[MarketingReportItem]]:
    """
    精简列表接口 (POST)
    """
    # 1. 调用 Service (Service 已经返回了 List[MarketingReportItem])
    data = await service.get_demo_list(req_data.user_id, req_data.marketplace_id)

    # 2. 直接包装返回，Router 层不包含任何处理逻辑
    return ResponseModel.success(
        data=data, request_id=getattr(request.state, "request_id", None)
    )
