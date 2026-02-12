"""
File: app/domains/operations/repository.py
Description: 运营领域仓储层

职责：
1. OperationsReportRepository: 报告核心数据查询 (列表/详情/KPI/诊断)
2. OperationsLogRepository: 变化日志与审计日志的分页查询 (基于时间窗口)
3. OperationsQARepository: 问答上下文与会话管理

Author: jinmozhe
Created: 2026-02-12
"""

from datetime import date
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import asc, desc, func, select, update
from sqlalchemy.orm import load_only

from app.db.models.operations_report import (
    OperationsAuditLog,
    OperationsChangeLog,
    OperationsReport,
    OperationsReportQA,
)
from app.db.repositories.base import BaseRepository


class OperationsReportRepository(
    BaseRepository[OperationsReport, BaseModel, BaseModel]
):
    """
    运营报告主表仓储
    """

    async def get_flat_reports(
        self, user_id: str, marketplace_id: str, period_limit: int = 4
    ) -> list[OperationsReport]:
        """
        获取用户最近的报告列表 (元数据)。

        [Business Rule] 永远只返回最近的 N 个周期(Period)的数据。
        逻辑：
        1. 先找出最近的 period_limit 个唯一周期 (Start/End)。
        2. 再查找属于这些周期的所有报告记录。
        """

        # 1. 定义 CTE：找出最近的 N 个唯一周期
        target_periods_cte = (
            select(OperationsReport.period_start, OperationsReport.period_end)
            .where(
                OperationsReport.user_id == user_id,
                OperationsReport.marketplace_id == marketplace_id,
            )
            .group_by(
                OperationsReport.period_start, OperationsReport.period_end
            )  # 去重
            .order_by(desc(OperationsReport.period_start))  # 倒序
            .limit(period_limit)  # 限制周期数量 (默认4)
            .cte("target_periods")
        )

        # 2. 主查询：Inner Join 这个 CTE
        stmt = (
            select(OperationsReport)
            .options(
                load_only(
                    OperationsReport.id,
                    OperationsReport.week,
                    OperationsReport.ad_type,
                    OperationsReport.period_start,
                    OperationsReport.period_end,
                    OperationsReport.report_type,
                    OperationsReport.report_source,
                    OperationsReport.pdf_path,
                )
            )
            .join(
                target_periods_cte,
                (OperationsReport.period_start == target_periods_cte.c.period_start)
                & (OperationsReport.period_end == target_periods_cte.c.period_end),
            )
            .where(
                OperationsReport.user_id == user_id,
                OperationsReport.marketplace_id == marketplace_id,
            )
            .order_by(desc(OperationsReport.period_start))
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
    ) -> OperationsReport | None:
        """
        获取最新的一份详细报告 (包含 KPI 和 Diagnosis)。
        """
        stmt = (
            select(OperationsReport)
            .where(
                OperationsReport.user_id == user_id,
                OperationsReport.marketplace_id == marketplace_id,
                OperationsReport.ad_type == ad_type,
                OperationsReport.report_type == report_type,
                OperationsReport.report_source == report_source,
            )
            .order_by(desc(OperationsReport.period_start))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class OperationsLogRepository(
    BaseRepository[OperationsChangeLog, BaseModel, BaseModel]
):
    """
    运营日志仓储 (负责 ChangeLog 和 AuditLog)
    """

    async def get_change_logs(
        self,
        user_id: str,
        marketplace_id: str,
        period_start: date,
        period_end: date,
        category: str,
        page: int,
        page_size: int,
    ) -> tuple[list[OperationsChangeLog], int]:
        """
        分页获取三维变化记录
        """
        # 1. 构建基础查询条件
        base_filters = [
            OperationsChangeLog.user_id == user_id,
            OperationsChangeLog.marketplace_id == marketplace_id,
            OperationsChangeLog.period_start == period_start,
            OperationsChangeLog.period_end == period_end,
            OperationsChangeLog.category == category,
        ]

        # 2. 计算总数 (Count)
        count_stmt = select(func.count()).where(*base_filters)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        # 3. 分页查询 (Data)
        stmt = (
            select(OperationsChangeLog)
            .where(*base_filters)
            .order_by(desc(OperationsChangeLog.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def get_audit_logs(
        self,
        user_id: str,
        marketplace_id: str,
        period_start: date,
        period_end: date,
        category: str,
        page: int,
        page_size: int,
    ) -> tuple[list[OperationsAuditLog], int]:
        """
        分页获取操作审计日志
        """
        # 1. 构建基础查询条件
        base_filters = [
            OperationsAuditLog.user_id == user_id,
            OperationsAuditLog.marketplace_id == marketplace_id,
            OperationsAuditLog.period_start == period_start,
            OperationsAuditLog.period_end == period_end,
            OperationsAuditLog.category == category,
        ]

        # 2. 计算总数
        count_stmt = select(func.count()).where(*base_filters)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        # 3. 分页查询
        stmt = (
            select(OperationsAuditLog)
            .where(*base_filters)
            .order_by(desc(OperationsAuditLog.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        return items, total


class OperationsQARepository(BaseRepository[OperationsReportQA, BaseModel, BaseModel]):
    """
    运营问答仓储
    """

    async def get_report_context(self, report_id: UUID) -> dict | None:
        """
        [RAG Core] 获取 RAG 所需的上下文数据 (mcp_data)。
        """
        stmt = select(OperationsReport.mcp_data).where(OperationsReport.id == report_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_qa_by_id(self, qa_id: UUID) -> OperationsReportQA | None:
        """
        获取单条问答记录。
        """
        stmt = select(OperationsReportQA).where(OperationsReportQA.id == qa_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_qa_record(
        self, user_id: str, marketplace_id: str, report_id: UUID, question: str
    ) -> OperationsReportQA:
        """
        创建一条初始状态(PENDING)的问答记录。
        """
        qa_record = OperationsReportQA(
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
            update(OperationsReportQA)
            .where(OperationsReportQA.id == qa_id)
            .values(status=status)
        )
        await self.session.execute(stmt)

    async def update_answer(self, qa_id: UUID, answer: str, status: str) -> None:
        """
        更新最终回答内容和状态。
        """
        stmt = (
            update(OperationsReportQA)
            .where(OperationsReportQA.id == qa_id)
            .values(answer=answer, status=status)
        )
        await self.session.execute(stmt)

    async def get_chat_history(
        self, user_id: str, marketplace_id: str, report_id: UUID
    ) -> list[OperationsReportQA]:
        """
        获取指定报告的对话历史，按时间正序排列。
        """
        stmt = (
            select(OperationsReportQA)
            .where(
                OperationsReportQA.report_id == report_id,
                OperationsReportQA.user_id == user_id,
                OperationsReportQA.marketplace_id == marketplace_id,
            )
            .order_by(asc(OperationsReportQA.created_at))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_history(
        self, report_id: UUID, current_qa_id: UUID, limit: int = 5
    ) -> list[OperationsReportQA]:
        """
        [RAG Context] 获取当前对话之前的最近 N 条历史记录。
        用于构建 LLM 的 Multi-turn Context。
        """
        stmt = (
            select(OperationsReportQA)
            .where(
                OperationsReportQA.report_id == report_id,
                OperationsReportQA.id != current_qa_id,  # 排除当前这条
                OperationsReportQA.status == "COMPLETED",  # 必须是已完成的
                OperationsReportQA.answer.is_not(None),  # 必须有回答
            )
            .order_by(desc(OperationsReportQA.created_at))  # 倒序取最近的
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        # 翻转为正序 (时间轴: 旧 -> 新)，符合 LLM 阅读习惯
        return list(reversed(list(result.scalars().all())))
