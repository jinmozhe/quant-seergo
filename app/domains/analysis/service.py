"""
File: app/domains/analysis/service.py
Description: 分析领域服务层
Updated: 2026-02-04 (Allow returning None for empty state)
"""

from typing import Any

# 移除不再需要的导入
# from app.core.exceptions import AppException
from app.core.logging import logger

# from app.domains.analysis.constants import AnalysisError
from app.domains.analysis.repository import AnalysisRepository
from app.domains.analysis.schemas import AnalysisLatestQuery


class AnalysisService:
    """
    分析结果业务逻辑类
    """

    def __init__(self, repo: AnalysisRepository):
        self.repo = repo

    # 返回类型注解增加 | None
    async def fetch_latest_payload(
        self, query: AnalysisLatestQuery
    ) -> dict[str, Any] | None:
        """
        获取指定维度的最新分析数据内容。
        """
        record = await self.repo.get_latest_payload(
            user_id=query.user_id,
            marketplace_id=query.marketplace_id,
            role=query.role,
            dimension_type=query.dimension_type,
        )

        if not record:
            # 变更决策：不再抛出 404 异常，而是记录 INFO 日志并返回 None
            # 这允许前端通过 data === null 优雅处理空状态
            logger.info(
                "analysis_result_empty",
                user_id=query.user_id,
                marketplace_id=query.marketplace_id,
                role=query.role,
                dimension_type=query.dimension_type,
            )
            return None

        return record.data_payload
