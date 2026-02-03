# FastAPI Standard Project

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%2B-316192?logo=postgresql)](https://www.postgresql.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red?logo=sqlalchemy)](https://www.sqlalchemy.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](./LICENSE)
[![Ruff](https://img.shields.io/badge/Code%20Style-Ruff-black)](https://github.com/astral-sh/ruff)

**工程规范构建的企业级 FastAPI 后端脚手架。**
严格遵循全链路异步、领域驱动设计 (DDD) 与类型安全标准。

[查看工程规范 (STANDARDS.md)](./STANDARDS.md) · [查看 AI 指令](./.github/copilot-instructions.md) · [报告问题](../../issues)

</div>

---

## 📖 目录

- [核心架构特性](#-核心架构特性-architecture-philosophy)
- [项目结构](#-项目结构)
- [快速开始](#-快速开始-quick-start)
- [开发工作流](#-开发工作流-development-workflow)
- [API 响应契约](#-api-响应契约-unified-response)
- [部署与运维](#-部署与运维)
- [AI 辅助开发](#-ai-辅助开发)

---

## 📘 核心架构特性 (Architecture Philosophy)

本项目不仅仅是一个模板，它是 **[STANDARDS.md](./STANDARDS.md)** 规范的参考实现：

- **⚡ Async First**: 全链路异步设计 (`async`/`await`)，数据库驱动采用 `asyncpg`，拒绝阻塞 I/O。
- **🛡️ Typed ORM**: 强制使用 SQLAlchemy 2.0 (`Mapped` + `DeclarativeBase`)，拒绝隐式类型。
- **🏗️ Domain-Oriented**: 严格的领域分层架构：
    - **Router**: 仅负责 HTTP 协议解析与响应封装。
    - **Service**: 负责业务逻辑、事务控制与领域日志。
    - **Repository**: 仅负责通用数据持久化与查询。
- **🆔 UUID v7**: 数据库主键与 Request ID 全栈统一使用 UUID v7 (兼具随机性与时间有序性)。
- **📦 Unified Response**: 强制统一响应信封 (`ResponseModel`)，业务错误返回 HTTP 200 + 业务码。
- **🔒 Security & Log**: 集成 PII 敏感信息脱敏，基于 Loguru 的结构化 JSON 日志，全链路追踪。
- **🤖 AI-Ready**: 内置 Cursor/Copilot 提示词配置，让 AI 自动遵守项目规范。

---

## 📂 项目结构

```text
app/
  ├── api/               # 全局依赖、鉴权与通用组件
  ├── core/              # 核心基础设施 (配置, 日志, 异常, 响应封装)
  ├── db/                # 数据库层
  │   ├── models/        # 所有 ORM 模型 (UUIDModel 基类)
  │   └── repositories/  # 通用 Repository 基类
  ├── domains/           # 业务领域模块 (Bounded Contexts)
  │   └── users/         # 示例: 用户领域
  │       ├── router.py        # HTTP 接口
  │       ├── service.py       # 业务逻辑 (事务/校验)
  │       ├── repository.py    # 数据访问 (SQL)
  │       └── schemas.py       # Pydantic 模型
  ├── services/          # 跨领域业务编排 (Use Cases / Workflows)
  └── utils/             # 无状态通用工具 (如 PII Masking)
tests/                   # Pytest 测试套件 (Unit + Integration)
alembic/                 # 数据库迁移脚本
scripts/                 # 运维脚本
```

---

## 🚀 快速开始 (Quick Start)

### 1. 环境准备

确保本地已安装 `Python 3.11+` 和 `PostgreSQL`。

```bash
# 克隆项目
git clone [https://github.com/jinmozhe/fastapi_standard.git](https://github.com/jinmozhe/fastapi_standard.git)
cd fastapi_standard_project

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 安装 Pre-commit 钩子 (代码提交时自动检查)
pre-commit install
```

### 2. 配置环境变量

```bash
cp .env.example .env
```
编辑 `.env` 文件，确保 `DATABASE_URL` 指向你的本地 PostgreSQL 实例。

### 3. 数据库初始化

```bash
# 应用数据库迁移
alembic upgrade head

# (可选) 填充种子数据
python scripts/seed_data.py
```

### 4. 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问文档：
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🛠️ 开发工作流 (Development Workflow)

### 数据库迁移 (Alembic)

当你修改了 `app/db/models` 下的模型后：

```bash
# 1. 生成迁移脚本 (自动检测变更)
alembic revision --autogenerate -m "描述你的变更"

# 2. 检查生成的 alembic/versions/xxxx.py 文件

# 3. 应用变更到数据库
alembic upgrade head
```

### 运行测试

项目集成了 `pytest-asyncio`。

```bash
# 运行所有测试
pytest

# 运行特定测试并显示详细信息
pytest tests/unit/test_users.py -vv
```

### 代码规范检查

```bash
# 手动运行 Ruff 检查
ruff check .
ruff format .
```

---

## 📦 API 响应契约 (Unified Response)

所有接口统一返回以下 JSON 格式：

### 成功响应 (HTTP 200)
```json
{
  "code": 20000,
  "message": "Success",
  "data": {
    "id": "018e65c9-3a5b-7b22-8c4d-9e5f1a2b3c4d",
    "email": "user@example.com"
  },
  "request_id": "018e65c9-...",
  "timestamp": "2024-03-20T10:00:00Z"
}
```

### 业务错误响应 (HTTP 200)
```json
{
  "code": 40001,
  "message": "User already exists",
  "error": {
    "type": "BusinessError",
    "detail": "Email 'user@example.com' is already registered",
    "field": "email"
  },
  "request_id": "018e65c9-...",
  "timestamp": "2024-03-20T10:00:00Z"
}
```

---

## 🐳 部署与运维

使用 Docker Compose 快速启动全栈环境（App + DB）：

```bash
# 构建并后台启动
docker-compose up -d --build

# 查看实时日志
docker-compose logs -f app
```

---

## 🤖 AI 辅助开发

本项目针对 **GitHub Copilot** 和 **Cursor** 进行了深度优化。

1.  **Source of Truth**: 根目录下的 `STANDARDS.md` 是项目最高准则。
2.  **Copilot 配置**: `.github/copilot-instructions.md` 已预置，AI 会自动遵守以下规则：
    * ❌ 禁止在 Router 中写 SQL。
    * ❌ 禁止使用同步 DB 驱动。
    * ✅ 自动生成 UUID v7 主键。
    * ✅ 自动应用 PII 脱敏逻辑。

建议在 VS Code 中安装 GitHub Copilot 插件以获得最佳体验。

---

## 📄 License

MIT © [jinmozhe](https://github.com/jinmozhe)
