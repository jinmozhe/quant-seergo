"""
File: app/domains/marketing/constants.py
Description: 营销领域常量与错误码定义

包含：
1. MarketingErrorCode: 领域专用错误码 (继承自 BaseErrorCode)
2. 遵循格式: {domain}.{reason}

Author: jinmozhe
Created: 2026-02-04
"""

from app.core.error_code import BaseErrorCode


class MarketingErrorCode(BaseErrorCode):
    """
    营销领域错误码
    """

    # --- 404 Not Found ---
    REPORT_NOT_FOUND = (404, "marketing.report_not_found", "关联的分析报告不存在")
    QA_SESSION_NOT_FOUND = (404, "marketing.qa_session_not_found", "问答会话不存在")
    REPORT_CONTEXT_MISSING = (
        404,
        "marketing.context_missing",
        "报告核心数据缺失，无法分析",
    )

    # --- 502 External Service Error ---
    LLM_GENERATION_FAILED = (502, "marketing.llm_failed", "AI 服务调用失败，请稍后重试")
