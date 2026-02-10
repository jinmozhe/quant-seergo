"""
File: app/domains/marketing/repository.py
Description: 营销领域仓储层

包含：
1. MarketingReportRepository: 报告数据的查询 (CTE 分组 Top-N 策略)
2. MarketingQARepository: 智能问答记录的持久化与状态更新

Author: jinmozhe
Created: 2026-02-03
Updated: 2026-02-10 (Implement Top-4 Periods Logic)
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
        self, user_id: str, marketplace_id: str, period_limit: int = 4
    ) -> list[MarketingReport]:
        """
        获取用户最近的报告列表。

        [Business Rule] 永远只返回最近的 N 个周期(Period)的数据。
        逻辑：
        1. 先找出最近的 period_limit 个唯一周期 (Start/End)。
        2. 再查找属于这些周期的所有报告记录。
        """

        # 1. 定义 CTE：找出最近的 N 个唯一周期
        # SELECT distinct period_start, period_end FROM table ... ORDER BY start DESC LIMIT 4
        target_periods_cte = (
            select(MarketingReport.period_start, MarketingReport.period_end)
            .where(
                MarketingReport.user_id == user_id,
                MarketingReport.marketplace_id == marketplace_id,
            )
            .group_by(MarketingReport.period_start, MarketingReport.period_end)  # 去重
            .order_by(desc(MarketingReport.period_start))  # 倒序
            .limit(period_limit)  # 限制周期数量 (默认4)
            .cte("target_periods")
        )

        # 2. 主查询：Inner Join 这个 CTE
        # SELECT * FROM table JOIN cte ON period_match ...
        stmt = (
            select(
                MarketingReport.id,
                MarketingReport.week,
                MarketingReport.ad_type,
                MarketingReport.period_start,
                MarketingReport.period_end,
                MarketingReport.report_type,
                MarketingReport.report_source,
                MarketingReport.pdf_path,
            )
            .join(
                target_periods_cte,
                (MarketingReport.period_start == target_periods_cte.c.period_start)
                & (MarketingReport.period_end == target_periods_cte.c.period_end),
            )
            .where(
                MarketingReport.user_id == user_id,
                MarketingReport.marketplace_id == marketplace_id,
            )
            .order_by(desc(MarketingReport.period_start))
        )

        result = await self.session.execute(stmt)
        return list(result.all())  # type: ignore


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
        获取指定报告的对话历史，按时间正序排列。
        """
        stmt = (
            select(MarketingReportQA)
            .where(
                MarketingReportQA.report_id == report_id,
                MarketingReportQA.user_id == user_id,
                MarketingReportQA.marketplace_id == marketplace_id,
            )
            .order_by(asc(MarketingReportQA.created_at))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_history(
        self, report_id: UUID, current_qa_id: UUID, limit: int = 5
    ) -> list[MarketingReportQA]:
        """
        [RAG Context] 获取当前对话之前的最近 N 条历史记录。
        用于构建 LLM 的 Multi-turn Context (Sliding Window)。
        """
        stmt = (
            select(MarketingReportQA)
            .where(
                MarketingReportQA.report_id == report_id,
                MarketingReportQA.id != current_qa_id,  # 排除当前这条
                MarketingReportQA.status == "COMPLETED",  # 必须是已完成的
                MarketingReportQA.answer.is_not(None),  # 必须有回答
            )
            .order_by(desc(MarketingReportQA.created_at))  # 倒序取最近的
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        # 翻转为正序 (时间轴: 旧 -> 新)，符合 LLM 阅读习惯
        return list(reversed(list(result.scalars().all())))
