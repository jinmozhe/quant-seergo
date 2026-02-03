"""
File: app/domains/marketing/service.py
Description: 营销领域服务 (扁平版)
"""

# 这里我们只需要返回 DB 对象列表，Pydantic 会在 Router 层自动处理序列化
from app.db.models.marketing_report import MarketingReport
from app.domains.marketing.repository import MarketingReportRepository


class MarketingReportService:
    def __init__(self, repo: MarketingReportRepository):
        self.repo = repo

    async def get_demo_list(
        self, user_id: str, marketplace_id: str
    ) -> list[MarketingReport]:
        """
        获取演示用的扁平列表。
        """
        # 直接透传 Repository 的查询结果
        # 返回的是 Row 对象列表，Router 层的 response_model 会自动处理转换
        return await self.repo.get_flat_reports(user_id, marketplace_id, limit=100)
