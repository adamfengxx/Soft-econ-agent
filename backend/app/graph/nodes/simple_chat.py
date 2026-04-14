"""
Simple Chat 节点：处理简单对话，无需调用数据工具。
"""
from langchain_core.messages import AIMessage, SystemMessage

from app.graph.state import AgentState
from app.llm.client import get_streaming_llm
from app.prompts.simple_chat import SIMPLE_CHAT_PROMPT
from app.streaming.sse import emit_sse


async def simple_chat_node(state: AgentState, config) -> dict:
    llm = get_streaming_llm(temperature=0.7)

    response_style = state.get("response_style", "brief")
    style_note = (
        "\nKeep your response concise and direct."
        if response_style == "brief"
        else "\nProvide a thorough, well-structured response."
    )

    full_response = ""
    async for chunk in llm.astream([
        SystemMessage(content=SIMPLE_CHAT_PROMPT + style_note),
        *state.get("messages", []),
    ]):
        if chunk.content:
            full_response += chunk.content
            emit_sse("chat_token", {"token": chunk.content})

    emit_sse("done", {})

    return {"messages": [AIMessage(content=full_response)]}
