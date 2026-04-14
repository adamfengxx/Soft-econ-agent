from typing import Annotated, Optional, TypedDict
from langgraph.graph.message import add_messages
from app.models.schemas import Task


def _merge_task_results(
    existing: dict[str, str] | None,
    update: dict[str, str] | None,
) -> dict[str, str]:
    """
    task_results 的自定义 reducer。

    - update 为 None → 重置为空字典（跨轮隔离）
    - 否则 → 合并（同一轮内多个 worker 的结果累积）
    """
    if update is None:
        return {}
    if not existing:
        return update
    return existing | update


class AgentState(TypedDict, total=False):
    """
    LangGraph 图状态。

    total=False 表示所有字段均为可选，允许分步填充（节点只返回它更新的字段）。

    task_results 使用自定义 reducer：None 表示重置（跨轮隔离），dict 表示合并。
    """
    # 对话消息（add_messages reducer 保证追加而非覆盖）
    messages: Annotated[list, add_messages]

    # 本轮用户原始输入
    user_input: str

    # 意图分类结果
    intent: str  # "simple_chat" | "complex_research"

    # 回答风格："brief"（简要数据+解释）| "detailed"（完整报告）
    response_style: str

    # Planner 输出的任务列表
    tasks: list[Task]

    # Worker 执行结果 {task_id: result_text}
    # None → 跨轮重置；dict → 同轮内合并
    task_results: Annotated[dict[str, str], _merge_task_results]

    # Writer 最终报告
    final_report: str

    # 对话历史摘要（跨轮传递）
    conversation_history: str

    # 当前线程 ID（供 checkpointer 使用）
    thread_id: str

    # Coordinator 挑选出的当前待执行任务
    current_task: Optional[Task]

    # 前置任务结果汇总（注入给当前 worker）
    dependencies_context: str
