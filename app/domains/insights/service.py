"""
File: app/domains/insights/service.py
Description: 洞察领域服务层

职责：
1. InsightsReportService: 报告数据组装与 DTO 转换
2. InsightsQAService: RAG 核心逻辑 (MCP Data -> LLM Streaming -> DB Update)

Author: jinmozhe
Created: 2026-02-08
Updated: 2026-02-10 (Fix limit -> period_limit for Top-4 Periods)
"""

import json
from collections.abc import AsyncGenerator
from uuid import UUID

from loguru import logger
from openai import APIError, AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.core.config import settings
from app.core.exceptions import AppException
from app.domains.insights.constants import InsightsErrorCode
from app.domains.insights.repository import (
    InsightsQARepository,
    InsightsReportRepository,
)
from app.domains.insights.schemas import (
    ChatHistoryRequest,
    ChatInitRequest,
    ChatInitResponse,
    ChatRecordItem,
    InsightsReportItem,
    LatestReportRequest,
    LatestReportResponse,
)


class InsightsReportService:
    def __init__(self, repo: InsightsReportRepository):
        self.repo = repo

    async def get_demo_list(
        self, user_id: str, marketplace_id: str
    ) -> list[InsightsReportItem]:
        """
        获取报告列表 (精简版)
        """
        # [Updated] 使用 period_limit=4 获取最近的4个周期数据
        rows = await self.repo.get_flat_reports(user_id, marketplace_id, period_limit=4)
        return [InsightsReportItem.model_validate(row) for row in rows]

    async def get_latest_report(
        self, req: LatestReportRequest
    ) -> LatestReportResponse | None:
        """
        获取最新报告详情 (含大字段)
        """
        row = await self.repo.get_latest_report(
            user_id=req.user_id,
            marketplace_id=req.marketplace_id,
            ad_type=req.ad_type,
            report_type=req.report_type,
            report_source=req.report_source,
        )
        if not row:
            return None
        return LatestReportResponse.model_validate(row)


class InsightsQAService:
    """
    洞察智能问答服务 (RAG Core)
    """

    def __init__(self, repo: InsightsQARepository):
        self.repo = repo
        # 初始化 LLM 客户端
        self.llm_client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            timeout=60.0,
            max_retries=2,
        )

    async def init_chat(self, req: ChatInitRequest) -> ChatInitResponse:
        """
        第一步：初始化对话
        """
        # 1. 校验报告是否存在 (Fail Fast)
        # 仅检查是否存在 mcp_data
        mcp_data = await self.repo.get_report_context(req.report_id)
        if not mcp_data:
            raise AppException(InsightsErrorCode.REPORT_CONTEXT_MISSING)

        # 2. 创建 QA 记录 (PENDING)
        qa_record = await self.repo.create_qa_record(
            user_id=req.user_id,
            marketplace_id=req.marketplace_id,
            report_id=req.report_id,
            question=req.question,
        )

        # 3. 提交事务
        await self.repo.session.commit()
        await self.repo.session.refresh(qa_record)

        return ChatInitResponse(qa_id=qa_record.id)

    async def stream_answer_generator(self, qa_id: UUID) -> AsyncGenerator[str, None]:
        """
        第二步：流式生成答案 (Async Generator)
        """
        # 1. 获取 QA 记录
        qa_record = await self.repo.get_qa_by_id(qa_id)
        if not qa_record:
            yield "data: [ERROR] Session not found\n\n"
            return

        # 2. 获取上下文 (mcp_data Only)
        mcp_data = await self.repo.get_report_context(qa_record.report_id)
        if not mcp_data:
            yield "data: [ERROR] Report context data missing\n\n"
            return

        # 3. 更新状态: GENERATING
        await self.repo.update_status(qa_id, "GENERATING")
        await self.repo.session.commit()

        # 4. 构建 System Prompt
        # 直接序列化 mcp_data
        context_str = json.dumps(mcp_data, ensure_ascii=False)

        system_prompt = (
            "你是一个专业的广告营销数据分析师。请根据提供的 JSON 数据（MCP 洞察报告）"
            "回答用户的问题。\n"
            "要求：\n"
            "1. 引用具体数据支持你的观点。\n"
            "2. 回答风格专业、客观、简洁。\n"
            "3. 使用 Markdown 格式。\n"
            "4. 如果数据中没有相关信息，请明确说明，不要编造。"
        )

        # A. 基础系统消息
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": f"{system_prompt}\n\n数据:\n{context_str}"}
        ]

        # B. 注入历史记录 (Sliding Window Strategy)
        # 限制最近 5 条，防止 Token 爆炸，同时提供必要的对话上下文
        history_records = await self.repo.get_recent_history(
            report_id=qa_record.report_id,
            current_qa_id=qa_id,
            limit=5,
        )

        for record in history_records:
            if record.question and record.answer:
                # 必须按 User -> Assistant 顺序配对
                messages.append({"role": "user", "content": record.question})
                # [Critical] R1 模型优化: 仅注入最终 Answer，不注入 CoT (Reasoning)，保持上下文纯净
                messages.append({"role": "assistant", "content": record.answer})

        # C. 追加当前用户问题
        messages.append({"role": "user", "content": qa_record.question})

        full_answer_buffer = []

        try:
            # 5. 调用 LLM
            stream = await self.llm_client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=messages,
                stream=True,
                temperature=0.3,
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta
                content = delta.content

                if content:
                    full_answer_buffer.append(content)
                    # SSE 格式推送
                    yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"

            # 6. [闭环] 更新数据库
            final_answer = "".join(full_answer_buffer)
            await self.repo.update_answer(qa_id, final_answer, "COMPLETED")
            await self.repo.session.commit()

            yield "data: [DONE]\n\n"

        except APIError as e:
            logger.error(f"LLM API Error for qa_id={qa_id}: {e}")
            yield f"data: [ERROR] AI Service Error: {e.message}\n\n"
            await self._handle_failure(qa_id)

        except Exception as e:  # noqa: BLE001
            logger.error(f"Stream failed for qa_id={qa_id}: {e}")
            yield f"data: [ERROR] System Error: {str(e)}\n\n"
            await self._handle_failure(qa_id)

    async def _handle_failure(self, qa_id: UUID) -> None:
        """
        辅助: 失败状态回写
        """
        try:
            await self.repo.update_status(qa_id, "FAILED")
            await self.repo.session.commit()
        except Exception as db_e:  # noqa: BLE001
            logger.error(f"Failed to update DB status for qa_id={qa_id}: {db_e}")

    async def get_chat_history(self, req: ChatHistoryRequest) -> list[ChatRecordItem]:
        """
        获取对话历史
        """
        rows = await self.repo.get_chat_history(
            user_id=req.user_id,
            marketplace_id=req.marketplace_id,
            report_id=req.report_id,
        )
        return [ChatRecordItem.model_validate(row) for row in rows]
