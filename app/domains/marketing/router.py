"""
File: app/domains/marketing/router.py
Description: 营销领域路由层

职责：
1. 声明 API 契约 (Endpoint, Method, Body)
2. 调用 Service
3. 封装统一响应 (ResponseModel)
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.api.deps import DBSession
from app.core.response import ResponseModel
from app.domains.marketing.repository import (
    MarketingQARepository,
    MarketingReportRepository,
)
from app.domains.marketing.schemas import (
    ChatHistoryRequest,
    ChatInitRequest,
    ChatInitResponse,
    ChatRecordItem,
    MarketingReportItem,
    ReportListRequest,
)
from app.domains.marketing.service import MarketingQAService, MarketingReportService

router = APIRouter()


# ------------------------------------------------------------------------------
# Dependencies
# ------------------------------------------------------------------------------
async def get_marketing_service(session: DBSession) -> MarketingReportService:
    repo = MarketingReportRepository(model=None, session=session)  # type: ignore
    return MarketingReportService(repo)


async def get_qa_service(session: DBSession) -> MarketingQAService:
    # QA Service 需要 MarketingQARepository
    repo = MarketingQARepository(model=None, session=session)  # type: ignore
    return MarketingQAService(repo)


MarketingServiceDep = Annotated[MarketingReportService, Depends(get_marketing_service)]
QAServiceDep = Annotated[MarketingQAService, Depends(get_qa_service)]


# ------------------------------------------------------------------------------
# Endpoints: Reports
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
    data = await service.get_demo_list(req_data.user_id, req_data.marketplace_id)
    return ResponseModel.success(
        data=data, request_id=getattr(request.state, "request_id", None)
    )


# ------------------------------------------------------------------------------
# Endpoints: AI Chat (RAG)
# ------------------------------------------------------------------------------


@router.post(
    "/qa/ask",
    summary="初始化 AI 对话",
    description="提交问题和报告ID，创建一个待处理的问答记录。返回 qa_id。",
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
    summary="获取 AI 回答流 (SSE)",
    description="通过 SSE (Server-Sent Events) 实时获取 AI 生成的回答。流结束后后端自动保存完整记录。",
)
async def stream_chat_answer(
    qa_id: UUID,
    service: QAServiceDep,
) -> StreamingResponse:
    """
    Step 2: SSE 流式输出
    注意：此接口不返回 ResponseModel，而是直接返回 text/event-stream 流。
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
    summary="获取对话历史",
    description="返回指定报告的对话记录列表，按时间先后顺序排列。",
    response_model=ResponseModel[list[ChatRecordItem]],
)
async def get_chat_history_list(
    request: Request,
    req_data: ChatHistoryRequest,
    service: QAServiceDep,
) -> ResponseModel[list[ChatRecordItem]]:
    """
    Step 3: 获取历史记录 (用于页面刷新后恢复会话)
    """
    data = await service.get_chat_history(req_data)
    return ResponseModel.success(
        data=data, request_id=getattr(request.state, "request_id", None)
    )
