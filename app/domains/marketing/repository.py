"""
File: app/domains/marketing/repository.py
Description: 营销报告仓储层 (精简查询)
"""

from pydantic import BaseModel
from sqlalchemy import desc, select

from app.db.models.marketing_report import MarketingReport
from app.db.repositories.base import BaseRepository


class MarketingReportRepository(BaseRepository[MarketingReport, BaseModel, BaseModel]):
    async def get_flat_reports(
        self, user_id: str, marketplace_id: str, limit: int = 100
    ) -> list[MarketingReport]:
        """
        获取用户最近的报告列表 (元数据)。
        [Change] 仅查询必要字段，不包含 heavy 的 mcp_data。
        """
        stmt = (
            select(
                MarketingReport.id,
                MarketingReport.period_start,
                MarketingReport.period_end,
                MarketingReport.report_type,
                MarketingReport.report_source,
                # MarketingReport.mcp_data,  <-- [Removed] 移除重数据
                MarketingReport.pdf_path,
            )
            .where(
                MarketingReport.user_id == user_id,
                MarketingReport.marketplace_id == marketplace_id,
            )
            .order_by(desc(MarketingReport.period_start))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return result.all()  # type: ignore
