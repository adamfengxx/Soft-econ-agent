"""
Planner 节点：将用户研究需求拆解为带依赖关系的任务列表。
"""
from datetime import date

from app.graph.state import AgentState
from app.llm.wrapper import plan_tasks
from app.prompts.planner import PLANNER_SYSTEM_PROMPT, TOOL_DESCRIPTIONS
from app.streaming.sse import emit_sse


async def planner_node(state: AgentState, config) -> dict:
    conv_history = state.get("conversation_history", "")
    conv_section = (
        f"Previous conversation context:\n{conv_history}\n"
        if conv_history
        else ""
    )

    prompt = PLANNER_SYSTEM_PROMPT.format(
        today=date.today().isoformat(),
        conversation_history=conv_section,
        user_input=state["user_input"],
        available_tools=TOOL_DESCRIPTIONS,
    )

    tasks = await plan_tasks(
        prompt,
        state["user_input"],
        fallback_description=state["user_input"],
    )

    emit_sse("plan_generated", {"tasks": [t.model_dump() for t in tasks]})

    return {"tasks": tasks, "task_results": {}}
