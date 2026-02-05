"""
File: app/api_router.py
Description: 根 API 路由聚合层

本模块负责：
1. 聚合所有业务领域的 Router (auth, users, marketing, analysis)
2. 统一设置路由前缀 (如 /auth, /users)
3. 统一设置标签 (Tags) 用于 OpenAPI 文档分组

Author: jinmozhe
Created: 2025-12-05
Updated: 2026-02-04 (Add Analysis Domain)
"""

from fastapi import APIRouter

# 新增: Analysis 领域路由导入
from app.domains.analysis.router import router as analysis_router

# 导入领域路由
from app.domains.auth.router import router as auth_router
from app.domains.marketing.router import router as marketing_router
from app.domains.users.router import router as users_router

# 创建根 API 路由
api_router = APIRouter()

# ------------------------------------------------------------------------------
# 注册领域路由
# ------------------------------------------------------------------------------

# 1. 认证模块 (Auth Domain)
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])

# 2. 用户模块 (Users Domain)
api_router.include_router(users_router, prefix="/users", tags=["users"])

# 3. 营销模块 (Marketing Domain)
api_router.include_router(marketing_router, prefix="/marketing", tags=["marketing"])

# 4. 分析模块 (Analysis Domain) [新增]
# 包含获取最新多维度分析结果等接口
api_router.include_router(analysis_router, prefix="/analysis", tags=["analysis"])
