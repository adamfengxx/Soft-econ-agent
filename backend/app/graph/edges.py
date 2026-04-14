"""
图的条件路由函数。

架构：顺序任务执行（避免并行 Send API 的状态追踪复杂性）
  START → taker → route_by_intent → simple_chat → END
                                  → planner → coordinator → worker → check_progress
                                                 ↑                          |
                                                 └──── (more tasks) ────────┘
                                                                            → writer → END
"""
from app.graph.state import AgentState


def route_by_intent(state: AgentState) -> str:
    """Taker 完成后的路由：简单聊天 or 复杂研究。"""
    intent = state.get("intent", "simple_chat")
    if intent == "complex_research":
        return "complex_research"
    return "simple_chat"


def check_progress(state: AgentState) -> str:
    """
    Worker 完成后的路由：
    - 还有未完成任务 → coordinator（挑选下一个任务）
    - 全部完成 → writer（生成报告）
    """
    completed = set(state.get("task_results", {}).keys())
    all_task_ids = {t.id for t in state.get("tasks", [])}

    if all_task_ids and completed >= all_task_ids:
        return "writer"
    return "coordinator"
