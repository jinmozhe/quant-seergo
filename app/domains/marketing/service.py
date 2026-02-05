"""
File: app/domains/marketing/service.py
Description: 营销领域服务

职责：
1. 调用 Repository 获取数据
2. [关键] 执行数据转换 (Row -> Pydantic Model)
3. 返回标准化的领域对象列表供 Router 使用
"""

from app.domains.marketing.repository import MarketingReportRepository
from app.domains.marketing.schemas import MarketingReportItem


class MarketingReportService:
    def __init__(self, repo: MarketingReportRepository):
        self.repo = repo

    async def get_demo_list(
        self, user_id: str, marketplace_id: str
    ) -> list[MarketingReportItem]:
        """
        获取演示用的精简列表。

        Returns:
            list[MarketingReportItem]: 已经转换好的 Pydantic 模型列表
        """
        # 1. 获取 DB 原始行 (List[Row])
        rows = await self.repo.get_flat_reports(user_id, marketplace_id, limit=100)

        # 2. [逻辑层] 执行数据清洗与转换
        # 将 SQLAlchemy Row 对象转换为 Pydantic Schema
        # 这里是处理业务逻辑的最佳位置 (例如：如果有字段需要计算、格式化，就在这里做)
        items = [MarketingReportItem.model_validate(row) for row in rows]

        return items
