"""
File: app/domains/analysis/constants.py
Description: 分析领域常量与业务错误码定义
Author: jinmozhe
Created: 2026-02-04
"""

from enum import Enum

from app.core.error_code import BaseErrorCode


class AnalysisError(BaseErrorCode, Enum):
    """分析领域业务错误码"""

    # 格式: (HTTP_STATUS, "domain.reason", "中文消息")
    NOT_FOUND = (404, "analysis.not_found", "未找到指定的分析结果数据")
    INVALID_ROLE = (400, "analysis.invalid_role", "不支持的业务角色类型")


class AnalysisMsg:
    """业务文案常量"""

    FETCH_SUCCESS = "获取分析数据成功"
