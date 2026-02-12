"""
File: app/domains/operations/constants.py
Description: 运营领域常量与错误码定义

包含：
1. OperationsErrorCode: 领域专用错误码
2. 遵循规范: 4xx/5xx 错误分类及业务语义化描述

Author: jinmozhe
Created: 2026-02-12
"""

from app.core.error_code import BaseErrorCode


class OperationsErrorCode(BaseErrorCode):
    """
    运营领域错误码定义
    """

    # --- 404 Not Found ---
    REPORT_NOT_FOUND = (404, "operations.report_not_found", "关联的运营报告不存在")

    QA_SESSION_NOT_FOUND = (404, "operations.qa_session_not_found", "问答会话不存在")

    REPORT_CONTEXT_MISSING = (
        404,
        "operations.context_missing",
        "运营报告核心上下文(mcp_data)缺失，无法进行AI分析",
    )

    # --- 400 Bad Request ---
    INVALID_PERIOD = (
        400,
        "operations.invalid_period",
        "报告周期无效 (开始日期不能晚于结束日期)",
    )

    INVALID_LOG_CATEGORY = (400, "operations.invalid_category", "无效的内容分类")

    # --- 502 External Service Error ---
    LLM_GENERATION_FAILED = (
        502,
        "operations.llm_failed",
        "AI 服务调用异常，请稍后重试",
    )
