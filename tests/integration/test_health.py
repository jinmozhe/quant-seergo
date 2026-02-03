"""
File: tests/integration/test_health.py
Description: 健康检查接口集成测试

本模块测试 /health 端点。
注意：根据架构规范，健康检查接口是特例，不使用统一响应信封 (Unified Envelope)，
而是返回原始 JSON，以便 K8s/LB 能够简单解析。

Author: jinmozhe
Created: 2025-11-26
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    """
    测试：GET /health
    验证：
    1. 状态码 200
    2. 返回特定的原始 JSON {"status": "ok"}
    3. 不包含统一信封字段 (code, data, request_id)
    4. 中间件仍然工作：响应头中存在 X-Request-ID
    """
    # 注意：/health 挂载在根路径，没有 /api/v1 前缀
    response = await client.get("/health")

    # 1. 验证状态码
    assert response.status_code == 200

    # 2. 验证响应体
    data = response.json()
    assert data == {"status": "ok"}

    # 3. 反向验证：确保没有被统一信封包裹
    # 这是一个关键的架构约束检查：
    # 如果 Middleware 或 Router 意外地给 /health 加了信封，这里会报错
    assert "code" not in data
    assert "data" not in data
    assert "request_id" not in data

    # 4. 但中间件仍然应该生效：X-Request-ID 头存在
    request_id_header = response.headers.get("X-Request-ID")
    assert request_id_header is not None
    assert isinstance(request_id_header, str)
    assert request_id_header != ""
