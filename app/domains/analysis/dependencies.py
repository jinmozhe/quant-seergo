"""
File: app/domains/analysis/dependencies.py
Description: 分析领域依赖注入定义
Author: jinmozhe
Created: 2026-02-04
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db  # 假设全局 Session 注入定义在此
from app.domains.analysis.repository import AnalysisRepository
from app.domains.analysis.service import AnalysisService


async def get_analysis_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AnalysisRepository:
    """初始化 Repository 实例"""
    return AnalysisRepository(session)


async def get_analysis_service(
    repo: Annotated[AnalysisRepository, Depends(get_analysis_repository)],
) -> AnalysisService:
    """初始化 Service 实例"""
    return AnalysisService(repo)


# --- 强制标准：定义类型别名供 Router 使用 ---
AnalysisServiceDep = Annotated[AnalysisService, Depends(get_analysis_service)]
