"""
File: app/domains/insights/repository.py
Description: 洞察领域仓储层

职责：
1. InsightsReportRepository: 报告列表查询 (CTE 分组 Top-4 策略)
2. InsightsQARepository: 问答上下文获取与对话状态管理

Author: jinmozhe
Created: 2026-02-08
Updated: 2026-02-10 (Implement Top-4 Periods Logic via CTE)
"""

from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import asc, desc, select, update
from sqlalchemy.orm import load_only

from app.db.models.insights_report import InsightsReport
from app.db.models.insights_report_qa import InsightsReportQA
from app.db.repositories.base import BaseRepository


class InsightsReportRepository(BaseRepository[InsightsReport, BaseModel, BaseModel]):
    """
    洞察报告仓储
    """

    async def get_flat_reports(
        self, user_id: str, marketplace_id: str, period_limit: int = 4
    ) -> list[InsightsReport]:
        """
        获取用户最近的报告列表 (元数据)。

        [Business Rule] 永远只返回最近的 N 个周期(Period)的数据。
        逻辑：
        1. 先找出最近的 period_limit 个唯一周期 (Start/End)。
        2. 再查找属于这些周期的所有报告记录。
        """

        # 1. 定义 CTE：找出最近的 N 个唯一周期
        target_periods_cte = (
            select(InsightsReport.period_start, InsightsReport.period_end)
            .where(
                InsightsReport.user_id == user_id,
                InsightsReport.marketplace_id == marketplace_id,
            )
            .group_by(InsightsReport.period_start, InsightsReport.period_end)  # 去重
            .order_by(desc(InsightsReport.period_start))  # 倒序
            .limit(period_limit)  # 限制周期数量 (默认4)
            .cte("target_periods")
        )

        # 2. 主查询：Inner Join 这个 CTE
        stmt = (
            select(InsightsReport)
            .options(
                load_only(
                    InsightsReport.id,
                    InsightsReport.week,
                    InsightsReport.ad_type,
                    InsightsReport.period_start,
                    InsightsReport.period_end,
                    InsightsReport.report_type,
                    InsightsReport.report_source,
                    InsightsReport.pdf_path,
                )
            )
            .join(
                target_periods_cte,
                (InsightsReport.period_start == target_periods_cte.c.period_start)
                & (InsightsReport.period_end == target_periods_cte.c.period_end),
            )
            .where(
                InsightsReport.user_id == user_id,
                InsightsReport.marketplace_id == marketplace_id,
            )
            .order_by(desc(InsightsReport.period_start))
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_report(
        self,
        user_id: str,
        marketplace_id: str,
        ad_type: str,
        report_type: str,
        report_source: str,
    ) -> InsightsReport | None:
        """
        获取最新的一份详细报告 (包含所有大字段)。
        """
        stmt = (
            select(InsightsReport)
            .where(
                InsightsReport.user_id == user_id,
                InsightsReport.marketplace_id == marketplace_id,
                InsightsReport.ad_type == ad_type,
                InsightsReport.report_type == report_type,
                InsightsReport.report_source == report_source,
            )
            .order_by(desc(InsightsReport.period_start))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class InsightsQARepository(BaseRepository[InsightsReportQA, BaseModel, BaseModel]):
    """
    洞察问答仓储
    """

    async def get_report_context(self, report_id: UUID) -> dict | None:
        """
        [RAG Core] 获取 RAG 所需的上下文数据。

        [Updated] 仅返回 mcp_data 字段值，作为 AI 分析的核心依据。
        """
        stmt = select(InsightsReport.mcp_data).where(InsightsReport.id == report_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_qa_by_id(self, qa_id: UUID) -> InsightsReportQA | None:
        """
        获取单条问答记录。
        """
        stmt = select(InsightsReportQA).where(InsightsReportQA.id == qa_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_qa_record(
        self, user_id: str, marketplace_id: str, report_id: UUID, question: str
    ) -> InsightsReportQA:
        """
        创建一条初始状态(PENDING)的问答记录。
        """
        qa_record = InsightsReportQA(
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
            update(InsightsReportQA)
            .where(InsightsReportQA.id == qa_id)
            .values(status=status)
        )
        await self.session.execute(stmt)

    async def update_answer(self, qa_id: UUID, answer: str, status: str) -> None:
        """
        更新最终回答内容和状态。
        """
        stmt = (
            update(InsightsReportQA)
            .where(InsightsReportQA.id == qa_id)
            .values(answer=answer, status=status)
        )
        await self.session.execute(stmt)

    async def get_chat_history(
        self, user_id: str, marketplace_id: str, report_id: UUID
    ) -> list[InsightsReportQA]:
        """
        获取指定报告的对话历史，按时间正序排列。
        """
        stmt = (
            select(InsightsReportQA)
            .where(
                InsightsReportQA.report_id == report_id,
                InsightsReportQA.user_id == user_id,
                InsightsReportQA.marketplace_id == marketplace_id,
            )
            .order_by(asc(InsightsReportQA.created_at))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_history(
        self, report_id: UUID, current_qa_id: UUID, limit: int = 5
    ) -> list[InsightsReportQA]:
        """
        [RAG Context] 获取当前对话之前的最近 N 条历史记录。
        用于构建 LLM 的 Multi-turn Context。
        """
        stmt = (
            select(InsightsReportQA)
            .where(
                InsightsReportQA.report_id == report_id,
                InsightsReportQA.id != current_qa_id,  # 排除当前这条
                InsightsReportQA.status == "COMPLETED",  # 必须是已完成的
                InsightsReportQA.answer.is_not(None),  # 必须有回答
            )
            .order_by(desc(InsightsReportQA.created_at))  # 倒序取最近的
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        # 翻转为正序 (时间轴: 旧 -> 新)，符合 LLM 阅读习惯
        return list(reversed(list(result.scalars().all())))
