"""
Worker 节点：执行单个研究任务，支持多轮 tool calling。

实现了完整的 agentic loop：
  LLM 调用 → 返回 tool_calls → 并发执行工具 → 将结果送回 LLM → 循环直到无 tool_calls
"""
import asyncio
from datetime import date

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

from app.config import settings
from app.graph.state import AgentState
from app.llm.client import get_tool_llm
from app.models.schemas import Task
from app.prompts.worker import WORKER_SYSTEM_PROMPT
from app.streaming.sse import emit_sse
from app.tools.alpha_vantage import alpha_vantage_api
from app.tools.brave_search import brave_search
from app.tools.calculator import python_calculator
from app.tools.eurostat import eurostat_api
from app.tools.fred import fred_api
from app.tools.imf import imf_data_api
from app.tools.oecd import oecd_api
from app.tools.world_bank import world_bank_api

TOOLS = [world_bank_api, imf_data_api, oecd_api, eurostat_api, fred_api, alpha_vantage_api, brave_search, python_calculator]
TOOL_MAP = {t.name: t for t in TOOLS}


async def _invoke_tool(tool_name: str, tool_args: dict) -> str:
    """
    安全执行单个工具，返回结果字符串。

    始终使用 ainvoke()：LangChain 的 StructuredTool.ainvoke() 会自动处理
    sync/async 两种情况——async 工具直接 await coroutine，sync 工具通过
    asyncio.to_thread 在线程池中执行，无需手动判断。
    """
    tool_fn = TOOL_MAP.get(tool_name)
    if tool_fn is None:
        return f"[Error] Tool '{tool_name}' not found."
    try:
        result = await asyncio.wait_for(
            tool_fn.ainvoke(tool_args),
            timeout=settings.TOOL_CALL_TIMEOUT,
        )
        return str(result)
    except asyncio.TimeoutError:
        return f"[Error] {tool_name} timed out after {settings.TOOL_CALL_TIMEOUT}s."
    except Exception as e:
        return f"[Error] {tool_name} failed: {e}"


async def worker_node(state: AgentState, config) -> dict:
    task: Task | None = state.get("current_task")

    # 防御性检查：coordinator 应始终设置 current_task，但防止极端情况崩溃
    if task is None:
        return {}

    deps_context = state.get("dependencies_context", "")
    conv_history = state.get("conversation_history", "")

    emit_sse("task_status_update", {"task_id": task.id, "status": "running"})

    llm = get_tool_llm(TOOLS, temperature=0)

    dep_section = (
        f"\nResults from prerequisite tasks (use these, do NOT re-fetch):\n{deps_context}\n"
        if deps_context
        else ""
    )
    conv_section = (
        f"\nConversation history for context:\n{conv_history}\n"
        if conv_history
        else ""
    )

    system_prompt = WORKER_SYSTEM_PROMPT.format(
        today=date.today().isoformat(),
        task_id=task.id,
        task_description=task.description,
        dependencies_context_section=dep_section,
        conversation_history_section=conv_section,
    )

    messages: list = [SystemMessage(content=system_prompt)]

    for _ in range(settings.MAX_TOOL_ROUNDS):
        response: AIMessage = await llm.ainvoke(messages)

        if not response.tool_calls:
            # 无 tool calls → 最终回答
            result_text = response.content or ""
            emit_sse("worker_token", {"task_id": task.id, "token": result_text})
            emit_sse("task_status_update", {"task_id": task.id, "status": "completed"})
            return {"task_results": {task.id: result_text}}

        # 有 tool calls → 先追加 AI 消息，再并发执行所有工具
        messages.append(response)

        # 发出所有 tool_call_start 事件
        for tool_call in response.tool_calls:
            emit_sse("tool_call_start", {
                "task_id": task.id,
                "tool_name": tool_call["name"],
                "tool_input": tool_call["args"],
            })

        # 并发执行当次所有工具调用
        tool_results: list[str] = await asyncio.gather(*[
            _invoke_tool(tc["name"], tc["args"])
            for tc in response.tool_calls
        ])

        # 按序追加结果，保证 tool_call_id 对应关系正确
        for tool_call, tool_result in zip(response.tool_calls, tool_results):
            emit_sse("tool_call_result", {
                "task_id": task.id,
                "tool_name": tool_call["name"],
                "tool_output": tool_result[:1000],  # SSE payload 截断
            })
            messages.append(ToolMessage(
                content=tool_result[:settings.MAX_TOOL_OUTPUT_TO_LLM],
                tool_call_id=tool_call["id"],
            ))

    # for 循环正常结束（未 return）→ 达到最大轮次
    result_text = (
        f"[Worker reached max tool rounds ({settings.MAX_TOOL_ROUNDS}). "
        "Partial result may be incomplete.]"
    )
    emit_sse("task_status_update", {"task_id": task.id, "status": "failed"})
    return {"task_results": {task.id: result_text}}
