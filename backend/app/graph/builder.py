from langgraph.graph import StateGraph, START, END

from app.graph.state import AgentState
from app.graph.nodes.taker import taker_node
from app.graph.nodes.planner import planner_node
from app.graph.nodes.worker import worker_node
from app.graph.nodes.writer import writer_node
from app.graph.nodes.simple_chat import simple_chat_node
from app.graph.nodes.coordinator import coordinator_node
from app.graph.edges import route_by_intent, check_progress
def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # ── 节点 ──────────────────────────────────────────────────────────────────
    graph.add_node("taker", taker_node)
    graph.add_node("simple_chat", simple_chat_node)
    graph.add_node("planner", planner_node)
    graph.add_node("coordinator", coordinator_node)
    graph.add_node("worker", worker_node)
    graph.add_node("writer", writer_node)

    # ── 边 ────────────────────────────────────────────────────────────────────
    # 入口 → Taker
    graph.add_edge(START, "taker")

    # Taker → 条件路由
    graph.add_conditional_edges(
        "taker",
        route_by_intent,
        {
            "simple_chat": "simple_chat",
            "complex_research": "planner",
        },
    )

    # Simple Chat → END
    graph.add_edge("simple_chat", END)

    # Planner → Coordinator（第一次挑选任务）
    graph.add_edge("planner", "coordinator")

    # Coordinator → Worker（执行当前任务）
    graph.add_edge("coordinator", "worker")

    # Worker → 检查进度
    graph.add_conditional_edges(
        "worker",
        check_progress,
        {
            "coordinator": "coordinator",  # 还有任务 → 继续
            "writer": "writer",           # 全部完成 → 生成报告
        },
    )

    # Writer → END
    graph.add_edge("writer", END)

    return graph


def get_compiled_graph(checkpointer):
    """编译图并挂载已初始化的 checkpointer。"""
    return build_graph().compile(checkpointer=checkpointer)
