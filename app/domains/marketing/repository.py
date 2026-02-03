"""
File: app/domains/marketing/repository.py
Description: 营销报告仓储层 (扁平版)
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
        获取用户最近的报告列表 (扁平数据)。
        包含 mcp_data, pdf_path 等所有展示字段。
        """
        stmt = (
            select(
                MarketingReport.id,  # 需要返回 ID
                MarketingReport.period_start,
                MarketingReport.period_end,
                MarketingReport.report_type,
                MarketingReport.report_source,
                MarketingReport.mcp_data,  # [新增] 核心数据
                MarketingReport.pdf_path,  # 下载路径
            )
            .where(
                MarketingReport.user_id == user_id,
                MarketingReport.marketplace_id == marketplace_id,
            )
            # 按开始时间倒序，最新的在前面
            .order_by(desc(MarketingReport.period_start))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return result.all()  # type: ignore
