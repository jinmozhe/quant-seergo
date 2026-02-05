"""
File: app/domains/analysis/repository.py
Description: 分析结果数据访问层
Author: jinmozhe
Created: 2026-02-04
"""

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.analysis_dimension_result import AnalysisDimensionResult


class AnalysisRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_latest_payload(
        self, user_id: str, marketplace_id: str, role: str, dimension_type: str
    ) -> AnalysisDimensionResult | None:
        """
        根据维度组合获取最后一条记录。
        由于使用 UUID v7，主键降序即为时间降序。
        """
        stmt = (
            select(AnalysisDimensionResult)
            .where(
                AnalysisDimensionResult.user_id == user_id,
                AnalysisDimensionResult.marketplace_id == marketplace_id,
                AnalysisDimensionResult.role == role,
                AnalysisDimensionResult.dimension_type == dimension_type,
            )
            .order_by(desc(AnalysisDimensionResult.id))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
