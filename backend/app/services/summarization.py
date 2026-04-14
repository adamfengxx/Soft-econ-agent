"""
长对话自动摘要压缩服务。

策略：
  - messages 表保存完整历史（永不删除）
  - threads.summary 缓存压缩摘要
  - 每积累 SUMMARIZE_THRESHOLD 条新消息触发一次压缩
  - 压缩时把"现有摘要 + 所有新消息"一起送给 LLM，输出新摘要
  - 下一轮 conversation_history 注入的是摘要，不是原始消息列表
    → 上下文长度恒定，不随对话轮数增长

跨轮任务隔离：
  - 每轮 chat 在 input_state 里显式重置 tasks / task_results 等字段
  - LangGraph checkpointer 只用于图执行状态，业务历史由本模块管理
"""
import logging

from langchain_core.messages import SystemMessage

from app.config import settings
from app.llm.client import get_chat_llm

logger = logging.getLogger(__name__)

_SUMMARY_SYSTEM_PROMPT = """\
You are a context manager for EconAgent, an AI-powered economic research assistant.

Your job: compress the conversation history below into a concise, information-dense summary \
that a future AI assistant can use as context.

{existing_summary_section}

Messages to incorporate:
{formatted_messages}

Write a summary under 400 words that preserves:
1. Main research questions and topics explored
2. Key data findings (specific numbers, countries, years, trends)
3. Conclusions and insights already reached
4. Any unresolved questions or pending follow-ups

Be precise and factual. Do NOT add new analysis—only summarize what was discussed.
"""


async def get_context_for_thread(thread_id: str, pool) -> str:
    """
    返回当前线程最佳的历史上下文字符串。

    如果有摘要则用摘要（定长），否则返回空字符串（首轮对话）。
    调用者将此字符串注入为 conversation_history。
    """
    from app.db.repositories.thread import get_thread

    thread = await get_thread(thread_id, pool)
    if thread is None:
        return ""
    return thread["summary"] or ""


async def summarize_if_needed(thread_id: str, pool) -> None:
    """
    检查是否需要触发摘要压缩，需要则异步生成并写回 DB。

    触发条件：自上次摘要以来新增消息数 >= settings.SUMMARIZE_THRESHOLD
    """
    from app.db.repositories.message import get_messages
    from app.db.repositories.thread import get_thread, update_summary

    thread = await get_thread(thread_id, pool)
    if thread is None:
        return

    new_since_summary = thread["message_count"] - thread["summary_up_to"]
    if new_since_summary < settings.SUMMARIZE_THRESHOLD:
        return

    try:
        messages = await get_messages(thread_id, pool)
        new_summary = await _generate_summary(thread["summary"] or "", messages)
        await update_summary(thread_id, new_summary, thread["message_count"], pool)
        logger.info(
            "Summary updated for thread %s (%d messages total)",
            thread_id,
            thread["message_count"],
        )
    except Exception as exc:
        # 摘要失败不影响主流程，只记录日志
        logger.warning("Summarization failed for thread %s: %s", thread_id, exc)


async def _generate_summary(existing_summary: str, messages: list[dict]) -> str:
    """调用 LLM 生成压缩摘要。"""
    existing_section = (
        f"Existing summary (from earlier in the conversation):\n{existing_summary}\n\n"
        if existing_summary
        else ""
    )
    formatted = "\n".join(
        f"[{m['role'].upper()}]: {m['content']}" for m in messages
    )
    prompt = _SUMMARY_SYSTEM_PROMPT.format(
        existing_summary_section=existing_section,
        formatted_messages=formatted,
    )
    llm = get_chat_llm()
    response = await llm.ainvoke([SystemMessage(content=prompt)])
    return response.content
