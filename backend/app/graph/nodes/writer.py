"""
Writer 节点：汇总所有 worker 结果，生成最终研究报告。
"""
from langchain_core.messages import AIMessage, SystemMessage

from app.graph.state import AgentState
from app.llm.client import get_streaming_llm
from app.models.schemas import Task
from app.prompts.writer import WRITER_SYSTEM_PROMPT
from app.streaming.sse import emit_sse


def _format_all_results(task_results: dict[str, str]) -> str:
    parts = []
    for task_id, result in task_results.items():
        parts.append(f"### {task_id}\n{result}")
    return "\n\n".join(parts)


def _format_task_plan(tasks: list[Task]) -> str:
    lines = []
    for task in tasks:
        dep_str = (
            f" (depends on: {', '.join(task.dependencies)})"
            if task.dependencies
            else ""
        )
        lines.append(f"- {task.id}: {task.description}{dep_str}")
    return "\n".join(lines)


async def writer_node(state: AgentState, config) -> dict:
    llm = get_streaming_llm(temperature=0.3)

    conv_history = state.get("conversation_history", "")
    conv_section = (
        f"\nPrevious conversation for context:\n{conv_history}\n"
        if conv_history
        else ""
    )

    response_style = state.get("response_style", "brief")
    style_instruction = (
        "Output format: BRIEF. Give a direct, concise answer. "
        "Lead with the key data/numbers, add 1-2 sentences of context. "
        "No lengthy sections, no executive summary, no Key Takeaways. "
        "Use a short bullet list only if comparing multiple items."
        if response_style == "brief"
        else
        "Output format: DETAILED. Write a full structured report in Markdown. "
        "Include ## sections, tables for comparisons, executive summary, analysis, and Key Takeaways."
    )

    prompt = WRITER_SYSTEM_PROMPT.format(
        user_input=state.get("user_input", ""),
        all_task_results=_format_all_results(state.get("task_results", {})),
        task_plan=_format_task_plan(state.get("tasks", [])),
        conversation_history_section=conv_section,
        style_instruction=style_instruction,
    )

    report = ""
    async for chunk in llm.astream([SystemMessage(content=prompt)]):
        if chunk.content:
            report += chunk.content
            emit_sse("report_token", {"token": chunk.content})

    emit_sse("done", {})

    return {
        "final_report": report,
        "messages": [AIMessage(content=report)],
    }
