"""
File: app/domains/users/router.py
Description: 用户领域 HTTP 路由层

本模块定义了用户管理的 API 端点。
遵循 V2.1 架构规范：
1. 注册接口 (POST /) 保持公开
2. 详情与更新接口 (GET/PATCH /me) 必须鉴权 (CurrentUser)
3. 移除不安全的 /{user_id} 接口，防止越权访问 (IDOR)
4. [Refactor] 统一使用 ResponseModel.success 类方法，移除全局魔法函数

Author: jinmozhe
Created: 2025-12-05
Updated: 2026-02-02 (Unified Response Style)
"""

from fastapi import APIRouter, Request, status

from app.api.deps import CurrentUser

# [Change] 移除 success 快捷函数导入，仅保留 ResponseModel 类
from app.core.response import ResponseModel

# 使用类型别名，代码极简
from app.domains.users.dependencies import UserServiceDep
from app.domains.users.schemas import UserCreate, UserRead, UserUpdate

router = APIRouter()


# ------------------------------------------------------------------------------
# Public Endpoints (公开接口)
# ------------------------------------------------------------------------------


@router.post(
    "",
    response_model=ResponseModel[UserRead],
    status_code=status.HTTP_201_CREATED,
    summary="注册新用户",
    description="创建新用户。需要提供手机号、密码等信息。手机号必须唯一。无需登录。",
)
async def create_user(
    request: Request,
    user_in: UserCreate,
    service: UserServiceDep,
) -> ResponseModel[UserRead]:
    """
    注册接口 (Public)
    """
    # 1. 调用 Service 执行业务逻辑
    user = await service.create(user_in)

    # 2. 获取 Request ID
    req_id = getattr(request.state, "request_id", None)

    # 3. 返回统一响应信封
    # [Change] 显式调用 ResponseModel.success 类方法
    return ResponseModel.success(
        data=UserRead.model_validate(user),
        request_id=req_id,
        message="User created successfully",
    )


# ------------------------------------------------------------------------------
# Protected Endpoints (受保护接口 - 需登录)
# ------------------------------------------------------------------------------


@router.get(
    "/me",
    response_model=ResponseModel[UserRead],
    summary="获取我的个人资料",
    description="获取当前登录用户的详细信息。需携带有效 Token。",
)
async def read_user_me(
    request: Request,
    current_user: CurrentUser,  # ✅ 核心：通过 Token 自动注入当前用户对象
) -> ResponseModel[UserRead]:
    """
    查询当前用户接口 (Secured)
    """
    # current_user 已经在 deps.py 中完成了鉴权、查库和状态校验
    # 直接返回即可，无需再次查询 Service
    req_id = getattr(request.state, "request_id", None)

    # [Change] 显式调用 ResponseModel.success 类方法
    return ResponseModel.success(
        data=UserRead.model_validate(current_user),
        request_id=req_id,
    )


@router.patch(
    "/me",
    response_model=ResponseModel[UserRead],
    summary="更新我的个人资料",
    description="更新当前登录用户的资料。支持修改密码、昵称等。需携带有效 Token。",
)
async def update_user_me(
    request: Request,
    user_in: UserUpdate,
    current_user: CurrentUser,  # ✅ 核心：确保只能修改自己
    service: UserServiceDep,
) -> ResponseModel[UserRead]:
    """
    更新当前用户接口 (Secured)
    """
    # 调用 Service 更新
    # 注意：这里传入 current_user.id，确保操作的是当前登录用户
    updated_user = await service.update(current_user.id, user_in)

    req_id = getattr(request.state, "request_id", None)

    # [Change] 显式调用 ResponseModel.success 类方法
    return ResponseModel.success(
        data=UserRead.model_validate(updated_user),
        request_id=req_id,
        message="User profile updated successfully",
    )
