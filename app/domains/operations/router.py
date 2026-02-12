"""
File: app/domains/operations/router.py
Description: 运营领域路由层

职责：
1. 声明 API 契约 (Endpoint Definitions)
2. 实现报告详情与流水日志 (Change/Audit) 的分流访问 (CQRS)
3. 封装统一响应 (ResponseModel / StreamingResponse)

Author: jinmozhe
Created: 2026-02-12
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.api.deps import DBSession
from app.core.response import ResponseModel
from app.domains.operations.repository import (
    OperationsLogRepository,
    OperationsQARepository,
    OperationsReportRepository,
)
from app.domains.operations.schemas import (
    AuditLogListRequest,
    AuditLogListResponse,
    ChangeLogListRequest,
    ChangeLogListResponse,
    ChatHistoryRequest,
    ChatInitRequest,
    ChatInitResponse,
    ChatRecordItem,
    LatestReportRequest,
    LatestReportResponse,
    OperationsReportItem,
    ReportListRequest,
)
from app.domains.operations.service import (
    OperationsLogService,
    OperationsQAService,
    OperationsReportService,
)

router = APIRouter()


# ------------------------------------------------------------------------------
# Dependencies
# ------------------------------------------------------------------------------
async def get_report_service(session: DBSession) -> OperationsReportService:
    repo = OperationsReportRepository(model=None, session=session)  # type: ignore
    return OperationsReportService(repo)


async def get_log_service(session: DBSession) -> OperationsLogService:
    repo = OperationsLogRepository(model=None, session=session)  # type: ignore
    return OperationsLogService(repo)


async def get_qa_service(session: DBSession) -> OperationsQAService:
    repo = OperationsQARepository(model=None, session=session)  # type: ignore
    return OperationsQAService(repo)


ReportServiceDep = Annotated[OperationsReportService, Depends(get_report_service)]
LogServiceDep = Annotated[OperationsLogService, Depends(get_log_service)]
QAServiceDep = Annotated[OperationsQAService, Depends(get_qa_service)]


# ------------------------------------------------------------------------------
# Endpoints: Reports (Aggregation Data)
# ------------------------------------------------------------------------------


@router.post(
    "/reports/list",
    summary="获取运营报告列表",
    description="获取最近 4 个周期的报告元数据，不含 KPI/诊断详情。",
    response_model=ResponseModel[list[OperationsReportItem]],
)
async def get_report_list(
    request: Request,
    req_data: ReportListRequest,
    service: ReportServiceDep,
) -> ResponseModel[list[OperationsReportItem]]:
    data = await service.get_demo_list(req_data.user_id, req_data.marketplace_id)
    return ResponseModel.success(
        data=data, request_id=getattr(request.state, "request_id", None)
    )


@router.post(
    "/reports/latest",
    summary="获取最新运营报告详情",
    description="获取最新一份报告的聚合数据 (KPI + 全域诊断看板)。",
    response_model=ResponseModel[LatestReportResponse],
)
async def get_latest_report_detail(
    request: Request,
    req_data: LatestReportRequest,
    service: ReportServiceDep,
) -> ResponseModel[LatestReportResponse]:
    data = await service.get_latest_report(req_data)
    return ResponseModel.success(
        data=data, request_id=getattr(request.state, "request_id", None)
    )


# ------------------------------------------------------------------------------
# Endpoints: Logs (Paginated Data)
# ------------------------------------------------------------------------------


@router.post(
    "/changes/list",
    summary="分页获取三维变化记录",
    description="按类型 (Risk, Opportunity...) 分页获取，默认每页 5 条。",
    response_model=ResponseModel[ChangeLogListResponse],
)
async def get_change_log_list(
    request: Request,
    req_data: ChangeLogListRequest,
    service: LogServiceDep,
) -> ResponseModel[ChangeLogListResponse]:
    data = await service.get_change_logs(req_data)
    return ResponseModel.success(
        data=data, request_id=getattr(request.state, "request_id", None)
    )


@router.post(
    "/audit/list",
    summary="分页获取操作审计日志",
    description="按类型 (Executed, Pending...) 分页获取，默认每页 5 条。",
    response_model=ResponseModel[AuditLogListResponse],
)
async def get_audit_log_list(
    request: Request,
    req_data: AuditLogListRequest,
    service: LogServiceDep,
) -> ResponseModel[AuditLogListResponse]:
    data = await service.get_audit_logs(req_data)
    return ResponseModel.success(
        data=data, request_id=getattr(request.state, "request_id", None)
    )


# ------------------------------------------------------------------------------
# Endpoints: AI Chat (RAG)
# ------------------------------------------------------------------------------


@router.post(
    "/qa/ask",
    summary="初始化运营 AI 对话",
    response_model=ResponseModel[ChatInitResponse],
)
async def init_chat_session(
    request: Request,
    req_data: ChatInitRequest,
    service: QAServiceDep,
) -> ResponseModel[ChatInitResponse]:
    data = await service.init_chat(req_data)
    return ResponseModel.success(
        data=data, request_id=getattr(request.state, "request_id", None)
    )


@router.get(
    "/qa/stream/{qa_id}",
    summary="获取运营 AI 回答流 (SSE)",
)
async def stream_chat_answer(
    qa_id: UUID,
    service: QAServiceDep,
) -> StreamingResponse:
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
    summary="获取运营对话历史",
    response_model=ResponseModel[list[ChatRecordItem]],
)
async def get_chat_history_list(
    request: Request,
    req_data: ChatHistoryRequest,
    service: QAServiceDep,
) -> ResponseModel[list[ChatRecordItem]]:
    data = await service.get_chat_history(req_data)
    return ResponseModel.success(
        data=data, request_id=getattr(request.state, "request_id", None)
    )
