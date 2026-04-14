"""
Coordinator 节点：从任务列表中挑选下一个可执行任务。

按依赖关系顺序执行，确保前置任务完成后才执行后续任务。
返回 current_task 和 dependencies_context，供 worker_node 使用。
"""
from app.graph.state import AgentState
from app.models.schemas import Task


def _build_deps_context(task: Task, task_results: dict[str, str]) -> str:
    """将当前任务的前置任务结果拼接为上下文字符串。"""
    if not task.dependencies:
        return ""
    parts = []
    for dep_id in task.dependencies:
        result = task_results.get(dep_id, "（前置任务结果未找到）")
        parts.append(f"[{dep_id} 结果]\n{result}")
    return "\n\n".join(parts)


async def coordinator_node(state: AgentState, config) -> dict:
    """
    挑选下一个满足依赖条件的待执行任务。

    逻辑：
    1. 收集已完成任务（task_results 的 key）
    2. 遍历任务列表，找到第一个未完成且依赖已满足的任务
    3. 返回 current_task 和 dependencies_context
    """
    completed = set(state.get("task_results", {}).keys())
    tasks: list[Task] = state.get("tasks", [])

    for task in tasks:
        if task.id in completed:
            continue
        deps_met = all(dep in completed for dep in task.dependencies)
        if deps_met:
            deps_context = _build_deps_context(task, state.get("task_results", {}))
            return {
                "current_task": task,
                "dependencies_context": deps_context,
            }

    # 所有任务已完成（check_progress 应已路由到 writer，此处兜底）
    return {"current_task": None, "dependencies_context": ""}
