"""
File: app/core/error_code.py
Description: 全局错误码基类与系统级错误定义
"""

from enum import Enum


class BaseErrorCode(Enum):
    """
    错误码基类。
    格式: (HTTP状态码, 业务码字符串, 默认描述文案)
    """

    def __init__(self, http_status: int, code: str, msg: str):
        self.http_status = http_status
        self.code = code
        self.msg = msg


class SystemErrorCode(BaseErrorCode):
    """系统级错误码 (10000-19999)"""

    SUCCESS = (200, "success", "操作成功")
    INVALID_PARAMS = (400, "system.invalid_params", "请求参数有误")
    UNAUTHORIZED = (401, "system.unauthorized", "身份验证失败")
    FORBIDDEN = (403, "system.forbidden", "权限不足")
    NOT_FOUND = (404, "system.not_found", "资源未找到")
    INTERNAL_ERROR = (500, "system.internal_error", "系统内部错误")
