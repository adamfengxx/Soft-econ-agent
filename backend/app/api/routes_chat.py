"""
POST /api/chat — 触发图执行并以 SSE 流式返回事件。

集成点：
  1. 每轮开始前从 DB 加载摘要作为 conversation_history（定长上下文）
  2. 显式重置任务字段，确保跨轮任务状态隔离
  3. 流结束后持久化消息，触发摘要压缩（如需要）
  4. 通过响应头 X-Thread-Id / X-User-Id 告知前端会话标识
"""
import json
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.db.repositories import message as message_repo
from app.db.repositories import thread as thread_repo
from app.services.auth import get_current_user_id
from app.services.summarization import get_context_for_thread, summarize_if_needed

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None  # 为空时自动生成（新会话）


@router.post("/api/chat")
async def chat(
    request: Request,
    body: ChatRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    接收用户消息，运行 LangGraph 图，以 SSE 流式返回所有事件。

    SSE 事件格式:
        event: <event_type>
        data: <json_payload>

    event_type 清单: intent_classified | plan_generated | task_status_update |
                     tool_call_start | tool_call_result | worker_token |
                     report_token | chat_token | done | error

    响应头:
        X-Thread-Id: <thread_id>  — 前端存储，用于后续多轮对话
    """
    thread_id = body.thread_id or str(uuid4())
    graph = request.app.state.graph
    pool = request.app.state.db_pool

    # 确保 user + thread 在 DB 中存在
    await thread_repo.get_or_create_thread(thread_id, user_id, pool)
    # 首条消息自动设为标题
    await thread_repo.set_title_if_empty(thread_id, body.message, pool)
    # 从 DB 加载摘要作为上下文（定长，不随轮次膨胀）
    conversation_history = await get_context_for_thread(thread_id, pool)

    async def event_generator():
        config = {"configurable": {"thread_id": thread_id}}

        input_state = {
            "user_input": body.message,
            "thread_id": thread_id,
            "conversation_history": conversation_history,
            "messages": [HumanMessage(content=body.message)],
            # ── 跨轮任务状态隔离 ──────────────────────────────────────────────
            # 每轮显式重置，防止上轮的 tasks/task_results 污染本轮图执行。
            # messages 字段由 add_messages reducer 管理，不在此重置。
            "tasks": [],
            "task_results": None,
            "current_task": None,
            "dependencies_context": "",
            "intent": "",
            "response_style": "brief",
            "final_report": "",
        }

        # 收集 assistant 输出，用于流结束后持久化
        assistant_tokens: list[str] = []

        try:
            async for chunk in graph.astream(
                input_state,
                config=config,
                stream_mode="custom",
            ):
                event_type = chunk.get("event", "unknown")
                data = chunk.get("data", {})

                # 拼接 report_token / chat_token 为完整 assistant 消息
                if event_type in ("report_token", "chat_token"):
                    assistant_tokens.append(data.get("token", ""))

                yield {
                    "event": event_type,
                    "data": json.dumps(data, ensure_ascii=False),
                }

        except Exception as exc:
            logger.exception("Graph execution error for thread %s", thread_id)
            yield {
                "event": "error",
                "data": json.dumps({"message": str(exc)}, ensure_ascii=False),
            }
            return  # 出错时跳过消息持久化

        # ── 流结束后：持久化消息 + 触发摘要 ─────────────────────────────────
        try:
            await message_repo.save_message(thread_id, "user", body.message, pool)
            await thread_repo.increment_message_count(thread_id, pool)

            assistant_content = "".join(assistant_tokens)
            if assistant_content:
                await message_repo.save_message(
                    thread_id, "assistant", assistant_content, pool
                )
                await thread_repo.increment_message_count(thread_id, pool)

            # 消息积累超过阈值时触发压缩（失败不影响主流程）
            await summarize_if_needed(thread_id, pool)

        except Exception as exc:
            logger.warning(
                "Failed to persist messages for thread %s: %s", thread_id, exc
            )

    return EventSourceResponse(
        event_generator(),
        headers={
            "X-Thread-Id": thread_id,
            "X-User-Id": user_id,
        },
    )
