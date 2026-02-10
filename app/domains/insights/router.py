"""
File: app/domains/insights/router.py
Description: 洞察领域路由层

职责：
1. 声明 API 契约
2. 调用 Insights 领域的 Service
3. 封装统一响应
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.api.deps import DBSession
from app.core.response import ResponseModel
from app.domains.insights.repository import (
    InsightsQARepository,
    InsightsReportRepository,
)
from app.domains.insights.schemas import (
    ChatHistoryRequest,
    ChatInitRequest,
    ChatInitResponse,
    ChatRecordItem,
    InsightsReportItem,
    LatestReportRequest,
    LatestReportResponse,
    ReportListRequest,
)
from app.domains.insights.service import InsightsQAService, InsightsReportService

router = APIRouter()


# ------------------------------------------------------------------------------
# Dependencies
# ------------------------------------------------------------------------------
async def get_insights_service(session: DBSession) -> InsightsReportService:
    repo = InsightsReportRepository(model=None, session=session)  # type: ignore
    return InsightsReportService(repo)


async def get_qa_service(session: DBSession) -> InsightsQAService:
    repo = InsightsQARepository(model=None, session=session)  # type: ignore
    return InsightsQAService(repo)


InsightsServiceDep = Annotated[InsightsReportService, Depends(get_insights_service)]
QAServiceDep = Annotated[InsightsQAService, Depends(get_qa_service)]


# ------------------------------------------------------------------------------
# Endpoints: Reports
# ------------------------------------------------------------------------------


@router.post(
    "/reports/list",
    summary="获取洞察报告列表",
    description="传入 user_id 和 marketplace_id，返回精简版报告列表 (不含 kpi/insights/ai 详情)。",
    response_model=ResponseModel[list[InsightsReportItem]],
)
async def get_report_list_demo(
    request: Request,
    req_data: ReportListRequest,
    service: InsightsServiceDep,
) -> ResponseModel[list[InsightsReportItem]]:
    """
    获取洞察报告列表
    """
    data = await service.get_demo_list(req_data.user_id, req_data.marketplace_id)
    return ResponseModel.success(
        data=data, request_id=getattr(request.state, "request_id", None)
    )


@router.post(
    "/reports/latest",
    summary="获取最新洞察报告详情",
    description="根据条件(user, market, type, source)获取最新一份报告的详细数据（含KPI/Insights/AI）。",
    response_model=ResponseModel[LatestReportResponse],
    # tags=["insights"]  <-- 已删除，由 api_router 统一管理
)
async def get_latest_report_detail(
    request: Request,
    req_data: LatestReportRequest,
    service: InsightsServiceDep,
) -> ResponseModel[LatestReportResponse]:
    """
    获取最新报告详情 (含大字段)
    """
    data = await service.get_latest_report(req_data)
    return ResponseModel.success(
        data=data, request_id=getattr(request.state, "request_id", None)
    )


# ------------------------------------------------------------------------------
# Endpoints: AI Chat (RAG)
# ------------------------------------------------------------------------------


@router.post(
    "/qa/ask",
    summary="初始化洞察 AI 对话",
    description="针对 Insights 报告初始化问答。提交问题，返回 qa_id。",
    response_model=ResponseModel[ChatInitResponse],
)
async def init_chat_session(
    request: Request,
    req_data: ChatInitRequest,
    service: QAServiceDep,
) -> ResponseModel[ChatInitResponse]:
    """
    Step 1: 初始化对话
    """
    data = await service.init_chat(req_data)
    return ResponseModel.success(
        data=data, request_id=getattr(request.state, "request_id", None)
    )


@router.get(
    "/qa/stream/{qa_id}",
    summary="获取洞察 AI 回答流 (SSE)",
    description="通过 SSE 流式获取 AI 针对 KPI/Insights 数据的分析结果。",
)
async def stream_chat_answer(
    qa_id: UUID,
    service: QAServiceDep,
) -> StreamingResponse:
    """
    Step 2: SSE 流式输出
    """
    return StreamingResponse(
        service.stream_answer_generator(qa_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/qa/history",
    summary="获取洞察对话历史",
    description="返回指定洞察报告的对话记录。",
    response_model=ResponseModel[list[ChatRecordItem]],
)
async def get_chat_history_list(
    request: Request,
    req_data: ChatHistoryRequest,
    service: QAServiceDep,
) -> ResponseModel[list[ChatRecordItem]]:
    """
    Step 3: 获取历史记录
    """
    data = await service.get_chat_history(req_data)
    return ResponseModel.success(
        data=data, request_id=getattr(request.state, "request_id", None)
    )
