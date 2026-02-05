"""
File: app/domains/marketing/service.py
Description: 营销领域服务

职责：
1. MarketingReportService: 报告列表数据转换
2. MarketingQAService: 编排 RAG 流程，调用 LLM，管理对话状态

Author: jinmozhe
Created: 2026-02-03
Updated: 2026-02-04 (Fix OpenAI Types & DeepSeek Config)
"""

import json
from collections.abc import AsyncGenerator
from uuid import UUID

from loguru import logger

# [Change] 引入 OpenAI 类型定义以修复 Pylance 报错
from openai import APIError, AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.core.config import settings
from app.core.exceptions import AppException
from app.domains.marketing.constants import MarketingErrorCode
from app.domains.marketing.repository import (
    MarketingQARepository,
    MarketingReportRepository,
)
from app.domains.marketing.schemas import (
    ChatHistoryRequest,
    ChatInitRequest,
    ChatInitResponse,
    ChatRecordItem,
    MarketingReportItem,
)


class MarketingReportService:
    def __init__(self, repo: MarketingReportRepository):
        self.repo = repo

    async def get_demo_list(
        self, user_id: str, marketplace_id: str
    ) -> list[MarketingReportItem]:
        """
        获取演示用的精简列表。
        """
        rows = await self.repo.get_flat_reports(user_id, marketplace_id, limit=100)
        items = [MarketingReportItem.model_validate(row) for row in rows]
        return items


class MarketingQAService:
    """
    营销智能问答服务 (RAG Core)
    """

    def __init__(self, repo: MarketingQARepository):
        self.repo = repo
        # 初始化 OpenAI 异步客户端 (复用 DeepSeek 配置)
        self.llm_client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            timeout=60.0,
            max_retries=2,
        )

    async def init_chat(self, req: ChatInitRequest) -> ChatInitResponse:
        """
        第一步：初始化对话。
        创建数据库记录，状态为 PENDING。
        """
        # 1. 校验 Report 是否存在
        mcp_data = await self.repo.get_report_mcp_data(req.report_id)
        if not mcp_data:
            raise AppException(MarketingErrorCode.REPORT_NOT_FOUND)

        # 2. 创建 QA 记录
        qa_record = await self.repo.create_qa_record(
            user_id=req.user_id,
            marketplace_id=req.marketplace_id,
            report_id=req.report_id,
            question=req.question,
        )

        # 3. 提交事务 (生成 ID)
        await self.repo.session.commit()
        await self.repo.session.refresh(qa_record)

        return ChatInitResponse(qa_id=qa_record.id)

    async def stream_answer_generator(self, qa_id: UUID) -> AsyncGenerator[str, None]:
        """
        第二步：流式生成答案 (Async Generator)。
        该函数会被 Router 的 StreamingResponse 消费。
        """
        # 1. 获取 QA 记录
        qa_record = await self.repo.get_qa_by_id(qa_id)
        if not qa_record:
            yield "data: [ERROR] Session not found\n\n"
            return

        # 2. 获取上下文 (mcp_data)
        mcp_data = await self.repo.get_report_mcp_data(qa_record.report_id)
        if not mcp_data:
            yield "data: [ERROR] Report context missing\n\n"
            return

        # 3. 更新状态: PENDING -> GENERATING
        await self.repo.update_status(qa_id, "GENERATING")
        await self.repo.session.commit()

        # 4. 准备 Prompt
        system_prompt = (
            "你是一个亚马逊广告营销专家。请根据提供的 JSON 数据（营销报告）回答用户问题。"
            "回答要专业、简洁，并使用 Markdown 格式。"
            "如果数据中没有相关信息，请直接说明。"
        )
        context_str = json.dumps(mcp_data, ensure_ascii=False)

        # [Fix] Pylance 错误修复：显式标注变量类型
        # 将 list[dict] 纠正为 list[ChatCompletionMessageParam]
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": f"{system_prompt}\n\n数据:\n{context_str}"},
            {"role": "user", "content": qa_record.question},
        ]

        full_answer_buffer = []

        try:
            # 5. 使用 OpenAI SDK 调用 DeepSeek
            stream = await self.llm_client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,  # 使用配置的模型 (如 deepseek-reasoner)
                messages=messages,  # 类型现在匹配了
                stream=True,
                temperature=0.5,
            )

            async for chunk in stream:
                # 获取内容增量
                # 注意：如果是 deepseek-reasoner，思考过程通常在 chunk.choices[0].delta.reasoning_content
                # 但标准 OpenAI SDK 可能将其放入 content 或需要特殊处理。
                # 目前 DeepSeek API 对兼容模式通常直接返回 content。
                delta = chunk.choices[0].delta
                content = delta.content

                if content:
                    full_answer_buffer.append(content)
                    # 实时推送 (SSE 格式: data: <json>\n\n)
                    yield f"data: {json.dumps({'content': content})}\n\n"

            # 6. [后端闭环] 流结束后，更新数据库为 COMPLETED
            final_answer = "".join(full_answer_buffer)
            await self.repo.update_answer(qa_id, final_answer, "COMPLETED")
            await self.repo.session.commit()

            # 发送结束信号
            yield "data: [DONE]\n\n"

        except APIError as e:
            # 捕获 OpenAI 库特定的 API 错误
            logger.error(f"LLM API Error for qa_id={qa_id}: {e}")
            yield f"data: [ERROR] AI Service Error: {e.message}\n\n"
            await self._handle_failure(qa_id)

        except Exception as e:  # noqa: BLE001
            # [Fix] BLE001: 显式忽略 Ruff 的 "Blind Exception" 警告
            # 必须捕获所有错误以防止数据库状态锁死
            logger.error(f"Stream failed for qa_id={qa_id}: {e}")
            yield f"data: [ERROR] System Error: {str(e)}\n\n"
            await self._handle_failure(qa_id)

    async def _handle_failure(self, qa_id: UUID) -> None:
        """
        辅助方法：处理失败状态回写
        """
        try:
            await self.repo.update_status(qa_id, "FAILED")
            await self.repo.session.commit()
        except Exception as db_e:  # noqa: BLE001
            logger.error(f"Failed to update DB status for qa_id={qa_id}: {db_e}")

    async def get_chat_history(self, req: ChatHistoryRequest) -> list[ChatRecordItem]:
        """
        获取对话历史列表
        """
        rows = await self.repo.get_chat_history(
            user_id=req.user_id,
            marketplace_id=req.marketplace_id,
            report_id=req.report_id,
        )
        return [ChatRecordItem.model_validate(row) for row in rows]
