"""
File: app/domains/users/constants.py
Description: 用户领域常量定义 (错误码枚举)
"""

from starlette.status import HTTP_409_CONFLICT

from app.core.error_code import BaseErrorCode


class UserErrorCode(BaseErrorCode):
    """用户领域错误码"""

    # 格式: (HTTP状态, 业务码, 默认文案)

    PHONE_EXIST = (HTTP_409_CONFLICT, "users.phone_exist", "该手机号已被注册")
    EMAIL_EXIST = (HTTP_409_CONFLICT, "users.email_exist", "该邮箱已被注册")
    USERNAME_EXIST = (HTTP_409_CONFLICT, "users.username_exist", "该用户名已被占用")
