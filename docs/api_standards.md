# 后端 API 接口与错误治理规范 (Modern Standard)

Version: 2.0.0 (Modern Edition)

Last Updated: 2026-01-15

Scope: 全栈开发团队 (Backend, Frontend, QA, SRE)

## 1. 核心设计哲学

为了提升开发体验 (DX) 与系统的可观测性，本项目弃用传统的“数字状态码 + 永远 200”模式，全面拥抱 **语义化 HTTP 状态码** 与 **字符串命名空间错误码**。

- **语义化 HTTP**: 让网关、缓存、监控系统能“读懂”请求结果（4xx 报警业务异常，5xx 报警系统故障）。
    
- **字符串错误码**: 让开发人员一眼看懂错误含义 (`auth.token_expired` vs `60103`)，彻底消除“号段冲突”与“查表痛苦”。
    
- **领域自治**: 错误定义下沉至各业务领域，实现模块的高内聚、低耦合。
    

---

## 2. 响应协议 (Response Protocol)

API 响应采用 **统一信封 (Unified Envelope)** 结构。

### 2.1 成功响应 (Success)

- **HTTP Status**: `200 OK` (查询/修改) 或 `201 Created` (创建资源)。
    
- **Code**: 固定为 `"success"`。
    

JSON

```
{
  "code": "success",
  "message": "登录成功",
  "data": {
    "token": "eyJhbGciOi...",
    "expires_in": 3600
  },
  "request_id": "req_01J8X..."
}
```

### 2.2 失败响应 (Error)

- **HTTP Status**: `4xx` (业务/客户端错误) 或 `5xx` (服务端故障)。
    
- **Code**: 格式为 `domain.reason` (命名空间.具体原因)。
    

JSON

```
{
  "code": "auth.password_error",       // 机器读：前端用于逻辑判断 (if code == '...')
  "message": "密码错误，您还有2次机会",  // 人读：直接展示给用户的文案
  "data": { "remaining_attempts": 2 }, // 补充数据 (可选)
  "request_id": "req_01J8X..."         // 追踪ID (必返)
}
```

---

## 3. 状态码与编码规范

### 3.1 HTTP 状态码映射表

我们精简使用以下 HTTP 状态码，涵盖 99% 的业务场景：

|**HTTP Status**|**含义**|**适用场景**|**监控策略**|
|---|---|---|---|
|**200 OK**|成功|大部分业务成功场景|✅ 正常|
|**400 Bad Request**|参数错误|Pydantic 校验失败、JSON 格式错误|⚠️ 忽略 (客户端问题)|
|**401 Unauthorized**|未认证|Token 缺失、无效、过期|⚠️ 忽略 (网关拦截)|
|**403 Forbidden**|禁止/逻辑错误|权限不足、**业务逻辑拦截** (如: 密码错/账户冻结)|⚠️ 关注 (业务异常)|
|**404 Not Found**|不存在|资源未找到 (用户不存在/订单不存在)|⚠️ 关注|
|**409 Conflict**|冲突|资源唯一性冲突 (手机号已注册)、并发冲突|🚨 **重点关注** (业务瓶颈)|
|**429 Too Many Requests**|限流|请求频率过高|⚠️ 关注|
|**500 Internal Error**|系统崩坏|数据库断连、代码 Bug (空指针)|🚨 **立刻报警 (P0)**|

### 3.2 业务错误码 (Code) 命名规范

格式：**`{domain}.{reason}`**

- **Domain**: 业务领域，全小写，与 `app/domains/` 目录名保持一致（如 `auth`, `order`, `payment`）。
    
- **Reason**: 具体原因，全小写下划线（snake_case），见名知意。
    

**✅ 正确示例**:

- `auth.user_not_found`
    
- `order.stock_insufficient`
    
- `payment.balance_low`
    

**❌ 错误示例**:

- `60401` (禁止使用数字)
    
- `UserNotFound` (禁止使用驼峰)
    
- `error` (禁止使用无意义泛称)
    

---

## 4. 工程实现指南

### 4.1 目录结构

Plaintext

```
app/
├── core/
│   ├── error_code.py      # [基座] 定义 BaseErrorCode 基类 + SystemErrorCode
│   ├── exceptions.py      # [逻辑] 异常类 + 自动映射 HTTP 状态码
│   └── response.py        # [信封] ResponseModel
└── domains/
    └── auth/              # [领域]
        ├── constants.py   # ✨ [定义] 该领域的 ErrorCode 和 Msg
        └── service.py     # [使用] raise AppException(AuthError.xxx)
```

### 4.2 核心代码实现

#### ① `app/core/error_code.py` (基类)

Python

```
from enum import Enum
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

class BaseErrorCode(Enum):
    """
    错误定义基类
    Value: (HTTP_Status, Code_String, Default_Message)
    """
    @property
    def http_status(self) -> int:
        return self.value[0]
    @property
    def code(self) -> str:
        return self.value[1]
    @property
    def msg(self) -> str:
        return self.value[2]

class SystemErrorCode(BaseErrorCode):
    """系统级通用错误"""
    # 400 参数错误 (Pydantic 校验会自动映射到这里)
    INVALID_PARAMS = (HTTP_400_BAD_REQUEST, "system.invalid_params", "参数校验失败")
    
    # 500 系统故障
    INTERNAL_ERROR = (HTTP_500_INTERNAL_SERVER_ERROR, "system.internal_error", "系统内部错误")
    DB_ERROR       = (HTTP_500_INTERNAL_SERVER_ERROR, "system.db_error", "数据库操作异常")
```

#### ② `app/core/exceptions.py` (智能处理器)

Python

```
from typing import Any
from fastapi import Request
from fastapi.responses import ORJSONResponse
from app.core.error_code import BaseErrorCode, SystemErrorCode
from app.core.response import ResponseModel

class AppException(Exception):
    def __init__(self, error: BaseErrorCode, message: str = "", data: Any = None):
        self.http_status = error.http_status
        self.code = error.code
        self.message = message or error.msg
        self.data = data

async def app_exception_handler(request: Request, exc: AppException):
    """自动将异常转换为对应的 HTTP 状态码响应"""
    return ORJSONResponse(
        status_code=exc.http_status,
        content=ResponseModel(
            code=exc.code,
            message=exc.message,
            data=exc.data,
            request_id=getattr(request.state, "request_id", None),
        ).model_dump(mode="json"),
    )
```

#### ③ `app/core/response.py` (响应信封)

Python

```
from typing import Generic, TypeVar, Any
from pydantic import BaseModel, Field

T = TypeVar("T")

class ResponseModel(BaseModel, Generic[T]):
    code: str = Field(default="success", description="业务状态码")
    message: str = Field(default="Success", description="响应信息")
    data: T | None = Field(default=None, description="业务数据")
    request_id: str | None = Field(default=None, description="请求追踪ID")

    @classmethod
    def success(cls, data: T | None = None, message: str = "Success", request_id: str | None = None):
        return cls(code="success", message=message, data=data, request_id=request_id)
```

---

## 5. 开发工作流 (Workflow)

当您开发一个新的功能模块（例如 `Orders`）时：

Step 1: 创建常量文件

新建 app/domains/orders/constants.py。

Step 2: 定义错误与消息

引入 BaseErrorCode，定义 HTTP 状态码与 String Code 的映射。

Python

```
from starlette.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT
from app.core.error_code import BaseErrorCode

class OrderError(BaseErrorCode):
    # 404: 资源不存在
    NOT_FOUND = (HTTP_404_NOT_FOUND, "order.not_found", "订单不存在")
    
    # 409: 业务冲突/无法处理
    STOCK_NOT_ENOUGH = (HTTP_409_CONFLICT, "order.stock_not_enough", "库存不足")
    
    # 403: 逻辑禁止
    STATUS_INVALID = (HTTP_403_FORBIDDEN, "order.status_invalid", "订单状态不允许此操作")

class OrderMsg:
    CREATE_SUCCESS = "订单创建成功"
```

Step 3: 业务层使用

在 service.py 中抛出异常，在 router.py 中返回成功。

Python

```
# Service
if stock < count:
    raise AppException(OrderError.STOCK_NOT_ENOUGH)

# Router
return ResponseModel.success(data=order, message=OrderMsg.CREATE_SUCCESS)
```

---

## 6. 前端对接指南

前端网络层（如 Axios Interceptor）建议逻辑：

1. **HTTP 状态码拦截**:
    
    - `2xx`: 进入业务处理。
        
    - `401`: 直接跳转登录页。
        
    - `5xx`: 提示“服务器开小差了”。
        
    - `400/403/404/409`: **不要抛出 Error，视为“业务失败”**，放行到下方处理 `response.data`。
        
2. **业务码处理**:
    
    - 读取 `response.data.code`。
        
    - `if code === 'success'`: 成功。
        
    - `else`: 弹出 `response.data.message` 或根据 `code` 字符串做特殊处理（如 `auth.user_not_found` 引导注册）。
