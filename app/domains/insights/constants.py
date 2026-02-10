"""
File: app/domains/insights/constants.py
Description: 洞察领域常量与错误码定义

包含：
1. InsightsErrorCode: 领域专用错误码 (继承自 BaseErrorCode)
2. 遵循格式: {domain}.{reason}

Author: jinmozhe
Created: 2026-02-08
"""

from app.core.error_code import BaseErrorCode


class InsightsErrorCode(BaseErrorCode):
    """
    洞察领域错误码
    """

    # --- 404 Not Found ---
    REPORT_NOT_FOUND = (404, "insights.report_not_found", "关联的洞察报告不存在")
    QA_SESSION_NOT_FOUND = (404, "insights.qa_session_not_found", "问答会话不存在")
    REPORT_CONTEXT_MISSING = (
        404,
        "insights.context_missing",
        "报告核心数据(KPI/Insights/AI)缺失，无法分析",
    )

    # --- 502 External Service Error ---
    LLM_GENERATION_FAILED = (502, "insights.llm_failed", "AI 服务调用失败，请稍后重试")
