"""
File: app/domains/marketing/router.py
Description: 营销领域路由层 (扁平演示版)

包含：
1. POST /list: 直接返回查询到的报告列表
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
    summary="获取报告列表 (Demo Flat)",
    description="传入 user_id 和 marketplace_id，直接返回最近的报告列表，无嵌套结构。",
    # 关键修改：直接返回 List[Item]，JSON 中 data 字段将直接是数组
    response_model=ResponseModel[list[MarketingReportItem]],
)
async def get_report_list_demo(
    request: Request,
    req_data: ReportListRequest,
    service: MarketingServiceDep,
) -> ResponseModel[list[MarketingReportItem]]:
    """
    扁平列表接口 (POST)
    """
    # 获取数据列表 (List[Row])
    rows = await service.get_demo_list(req_data.user_id, req_data.marketplace_id)

    # Pydantic 的 model_validate 会自动处理 List[Row] -> List[Model] 的转换
    # 只要 schemas.py 中配置了 from_attributes=True

    # 注意：SQLAlchemy select 返回的是 Row，
    # 如果是 select(Model) 返回的是 Model 对象，
    # 如果是 select(Col1, Col2...) 返回的是 Row(tuple-like)。
    # Pydantic v2 对 Row 的支持很好，可以直接转换。

    # 显式转换为 Pydantic Model 列表 (防御性编码)
    data = [MarketingReportItem.model_validate(row) for row in rows]

    return ResponseModel.success(
        data=data, request_id=getattr(request.state, "request_id", None)
    )
