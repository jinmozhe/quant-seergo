"""
File: app/domains/marketing/repository.py
Description: 营销领域仓储层

包含：
1. MarketingReportRepository: 报告数据的查询
2. MarketingQARepository: 智能问答记录的持久化与状态更新

Author: jinmozhe
Created: 2026-02-03
Updated: 2026-02-04 (Add get_chat_history)
"""

from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import asc, desc, select, update

from app.db.models.marketing_report import MarketingReport
from app.db.models.marketing_report_qa import MarketingReportQA
from app.db.repositories.base import BaseRepository


class MarketingReportRepository(BaseRepository[MarketingReport, BaseModel, BaseModel]):
    """
    营销报告仓储
    """

    async def get_flat_reports(
        self, user_id: str, marketplace_id: str, limit: int = 100
    ) -> list[MarketingReport]:
        """
        获取用户最近的报告列表 (元数据)。
        """
        stmt = (
            select(
                MarketingReport.id,
                MarketingReport.period_start,
                MarketingReport.period_end,
                MarketingReport.report_type,
                MarketingReport.report_source,
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


class MarketingQARepository(BaseRepository[MarketingReportQA, BaseModel, BaseModel]):
    """
    营销问答仓储
    """

    async def get_report_mcp_data(self, report_id: UUID) -> dict | None:
        """
        获取 RAG 所需的上下文数据 (mcp_data)。
        """
        stmt = select(MarketingReport.mcp_data).where(MarketingReport.id == report_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_qa_by_id(self, qa_id: UUID) -> MarketingReportQA | None:
        """
        获取单条问答记录。
        """
        stmt = select(MarketingReportQA).where(MarketingReportQA.id == qa_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_qa_record(
        self, user_id: str, marketplace_id: str, report_id: UUID, question: str
    ) -> MarketingReportQA:
        """
        创建一条初始状态(PENDING)的问答记录。
        """
        qa_record = MarketingReportQA(
            user_id=user_id,
            marketplace_id=marketplace_id,
            report_id=report_id,
            question=question,
            status="PENDING",
            answer=None,
        )
        self.session.add(qa_record)
        return qa_record

    async def update_status(self, qa_id: UUID, status: str) -> None:
        """
        仅更新状态。
        """
        stmt = (
            update(MarketingReportQA)
            .where(MarketingReportQA.id == qa_id)
            .values(status=status)
        )
        await self.session.execute(stmt)

    async def update_answer(self, qa_id: UUID, answer: str, status: str) -> None:
        """
        更新最终回答内容和状态。
        """
        stmt = (
            update(MarketingReportQA)
            .where(MarketingReportQA.id == qa_id)
            .values(answer=answer, status=status)
        )
        await self.session.execute(stmt)

    async def get_chat_history(
        self, user_id: str, marketplace_id: str, report_id: UUID
    ) -> list[MarketingReportQA]:
        """
        [New] 获取指定报告的对话历史，按时间正序排列。
        """
        stmt = (
            select(MarketingReportQA)
            .where(
                MarketingReportQA.report_id == report_id,
                MarketingReportQA.user_id == user_id,
                MarketingReportQA.marketplace_id == marketplace_id,
            )
            .order_by(asc(MarketingReportQA.created_at))  # 按时间先后顺序
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
