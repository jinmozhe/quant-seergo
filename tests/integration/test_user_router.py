"""
File: tests/integration/test_user_router.py
Description: 用户领域 HTTP 接口集成测试

本模块使用 httpx.AsyncClient 对 API 进行端到端测试，验证：
1. 路由挂载与 URL 路径 (/api/v1/users)
2. 统一响应信封结构 (ResponseModel)
3. 中间件行为 (X-Request-ID)
4. 完整的 CRUD 流程 (Create -> Get -> Patch)

Author: jinmozhe
Created: 2025-11-26
"""

import uuid

import pytest
from httpx import AsyncClient

from app.core.config import settings

# ------------------------------------------------------------------------------
# Integration Tests
# ------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_user_api(client: AsyncClient) -> None:
    """
    测试：POST /users 创建用户接口
    验证：
    1. 状态码 201
    2. 响应包含统一信封 (code=20000, request_id)
    3. 返回数据包含 id, created_at，且不含 password
    """
    payload = {
        "phone_number": "+8613800000010",
        "password": "strongpassword",
        "username": "api_user",
        "email": "api@example.com",
        "full_name": "API User",
    }

    # 完整路径：/api/v1/users
    response = await client.post(f"{settings.API_V1_STR}/users", json=payload)

    # 1. 验证 HTTP 状态码
    assert response.status_code == 201

    # 2. 验证统一响应信封
    body = response.json()
    assert body["code"] == 20000
    assert body["message"] == "User created successfully"
    assert body["request_id"] is not None  # 验证中间件生效

    # 验证响应头中的 Request-ID 与 body 一致
    assert response.headers.get("X-Request-ID") == body["request_id"]

    # 3. 验证业务数据
    user_data = body["data"]
    assert user_data["phone_number"] == payload["phone_number"]
    assert user_data["username"] == payload["username"]
    assert "id" in user_data
    assert "created_at" in user_data
    assert "password" not in user_data  # 确保密码未泄露


@pytest.mark.asyncio
async def test_get_user_api(client: AsyncClient) -> None:
    """
    测试：GET /users/{id} 查询接口
    流程：先创建 -> 再查询
    """
    # 1. 先创建一个用户
    create_payload = {
        "phone_number": "+8613800000011",
        "password": "password",
    }
    create_res = await client.post(f"{settings.API_V1_STR}/users", json=create_payload)
    assert create_res.status_code == 201
    created_body = create_res.json()
    user_id = created_body["data"]["id"]

    # 2. 查询该用户
    get_res = await client.get(f"{settings.API_V1_STR}/users/{user_id}")

    # 3. 验证 HTTP & 统一信封
    assert get_res.status_code == 200
    get_body = get_res.json()
    assert get_body["code"] == 20000
    assert get_body["request_id"] is not None
    assert get_res.headers.get("X-Request-ID") == get_body["request_id"]

    # 4. 验证业务数据
    data = get_body["data"]
    assert data["id"] == user_id
    assert data["phone_number"] == create_payload["phone_number"]
    assert "password" not in data


@pytest.mark.asyncio
async def test_update_user_api(client: AsyncClient) -> None:
    """
    测试：PATCH /users/{id} 更新接口
    验证：部分更新 (Patch)
    """
    # 1. 创建用户
    create_payload = {
        "phone_number": "+8613800000012",
        "password": "pwd",
        "full_name": "Old Name",
    }
    create_res = await client.post(f"{settings.API_V1_STR}/users", json=create_payload)
    assert create_res.status_code == 201
    user_id = create_res.json()["data"]["id"]

    # 2. 更新全名
    update_payload = {"full_name": "New Name"}
    patch_res = await client.patch(
        f"{settings.API_V1_STR}/users/{user_id}", json=update_payload
    )

    # 3. 验证统一信封
    assert patch_res.status_code == 200
    patch_body = patch_res.json()
    assert patch_body["code"] == 20000
    assert patch_body["message"] == "User updated successfully"
    assert patch_body["request_id"] is not None
    assert patch_res.headers.get("X-Request-ID") == patch_body["request_id"]

    # 4. 验证业务数据
    data = patch_body["data"]
    assert data["full_name"] == "New Name"
    # 确保其他字段未变
    assert data["phone_number"] == create_payload["phone_number"]
    assert "password" not in data


@pytest.mark.asyncio
async def test_error_handling_api(client: AsyncClient) -> None:
    """
    测试：异常处理与错误信封
    场景：查询不存在的用户 -> 404
    """
    random_id = str(uuid.uuid4())

    response = await client.get(f"{settings.API_V1_STR}/users/{random_id}")

    # 1. 验证 HTTP 状态码
    assert response.status_code == 404

    # 2. 验证错误信封结构
    body = response.json()
    assert body["code"] == 40400  # 对应 NotFoundException 的业务 code
    assert body["message"] == "用户不存在"
    assert body["error"]["type"] == "NotFoundException"
    assert body["request_id"] is not None
    assert response.headers.get("X-Request-ID") == body["request_id"]
