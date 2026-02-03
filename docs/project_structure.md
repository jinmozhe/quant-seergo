.
├── .env                          # [配置] 环境变量契约 (已配置 PostgreSQL/Redis 连接)
├── alembic.ini                   # [配置] Alembic 迁移工具的配置文件
├── README.md                     # [门户] 项目简介、快速启动指南
├── STANDARDS.md                  # [宪法] 项目工程规范与架构铁律 (Root Convention)
├── docs/                         # [文档] 具体技术文档归档 (Snake Case)
│   └── project_structure.md      # [架构] 详细目录结构说明
├── alembic/                      # [迁移] 数据库变更脚本目录
│   ├── env.py                    # [核心] 迁移环境配置 (同步驱动, 兼容 Windows/Linux)
│   └── script.py.mako            # [模板] 生成迁移文件的模板
├── app/                          # [源码] 应用核心代码
│   ├── main.py                   # [入口] FastAPI App 工厂、生命周期、静态资源挂载
│   ├── api_router.py             # [路由] 根路由聚合层 (Include Auth & Users Routers)
│   ├── api/                      # [API] 全局通用 API 组件
│   │   └── deps.py               # [依赖] DBSession, CurrentUser, SuperUser
│   ├── core/                     # [核心] 基础设施层
│   │   ├── config.py             # [配置] Pydantic Settings 定义
│   │   ├── exceptions.py         # [异常] 自定义异常与全局处理器
│   │   ├── logging.py            # [日志] Loguru 配置
│   │   ├── middleware.py         # [中间件] Request ID & Access Log (纯净版，无脱敏引用)
│   │   ├── redis.py              # [缓存] Redis 连接池管理
│   │   ├── response.py           # [响应] 统一响应信封 (Unified Envelope)
│   │   └── security.py           # [安全] 密码哈希 & JWT 工具
│   ├── db/                       # [数据库] 持久化层
│   │   ├── session.py            # [连接] AsyncEngine & SessionLocal
│   │   ├── models/               # [模型] SQLAlchemy ORM 模型
│   │   │   ├── __init__.py       # [注册] 导出所有模型供 Alembic 发现
│   │   │   ├── base.py           # [基类] UUIDModel, TimestampMixin, SoftDeleteMixin
│   │   │   ├── user.py           # [表] User 核心账号
│   │   │   ├── user_profile.py   # [表] UserProfile 档案
│   │   │   └── user_social.py    # [表] UserSocial 三方绑定
│   │   └── repositories/         # [仓储] 数据库访问层 (DAL)
│   │       └── base.py           # [基类] 通用 CRUD 封装
│   ├── domains/                  # [领域] 业务逻辑模块 (按功能拆分)
│   │   ├── auth/                 # -> 认证领域
│   │   │   ├── router.py         # 接口定义
│   │   │   ├── schemas.py        # 数据模型 (Pydantic)
│   │   │   └── service.py        # 业务逻辑 (Token Rotation)
│   │   └── users/                # -> 用户领域
│   │       ├── dependencies.py   # 依赖注入组装
│   │       ├── repository.py     # 专用仓储
│   │       ├── router.py         # 接口定义 (Anti-IDOR)
│   │       ├── schemas.py        # 数据模型
│   │       └── service.py        # 业务逻辑
│   ├── static/                   # [静态] 前端资源文件
│   │   ├── favicon.png           # 站点图标
│   │   └── redoc.standalone.js   # ReDoc 离线脚本
│   └── utils/                    # [工具] 通用工具库
│       └── masking.py            # [安全] PII 脱敏工具 (已就位，备用状态)
└── tests/                        # [测试] (待建设)
