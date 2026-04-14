"""
Taker 节点：意图分类。

将用户输入分类为 "simple_chat" 或 "complex_research"，
并通过 SSE 推送分类结果给前端。
"""
from app.graph.state import AgentState
from app.llm.wrapper import classify_intent
from app.prompts.taker import TAKER_SYSTEM_PROMPT
from app.streaming.sse import emit_sse


async def taker_node(state: AgentState, config) -> dict:
    intent, response_style = await classify_intent(TAKER_SYSTEM_PROMPT, state["user_input"])

    emit_sse("intent_classified", {"intent": intent, "response_style": response_style})

    return {"intent": intent, "response_style": response_style}
