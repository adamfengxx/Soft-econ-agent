"""
对话历史管理。

从 LangGraph checkpointer 中提取历史消息，格式化为文本注入给各节点。
"""
import logging

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


async def build_conversation_history(graph, thread_id: str) -> str:
    """
    从 checkpointer 提取历史对话，格式化为 [role]: content 文本。

    Args:
        graph: 已编译的 LangGraph 图
        thread_id: 会话 ID

    Returns:
        格式化的历史对话字符串，若无历史则返回空字符串
    """
    try:
        state = await graph.aget_state({"configurable": {"thread_id": thread_id}})
    except Exception as e:
        logger.warning("Failed to fetch conversation history for thread %s: %s", thread_id, e)
        return ""

    if not state or not state.values:
        return ""

    messages = state.values.get("messages", [])
    if not messages:
        return ""

    lines = []
    for msg in messages:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        # 只取文本内容（忽略 tool call 消息）
        content = msg.content if isinstance(msg.content, str) else ""
        if content.strip():
            lines.append(f"[{role}]: {content}")

    return "\n".join(lines)
