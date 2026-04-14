"""
SSE 事件推送模块。

使用 LangGraph 的 get_stream_writer() 从节点内部向 API 层推送自定义事件。
API 层通过 graph.astream(..., stream_mode="custom") 接收这些事件，
再格式化为 SSE 流推送给前端。
"""
from langgraph.config import get_stream_writer


def emit_sse(event_type: str, data: dict) -> None:
    """
    在 LangGraph 节点内部推送一条 SSE 事件。

    Args:
        event_type: SSE 事件类型，如 "intent_classified"、"worker_token" 等
        data: 事件 payload，必须可 JSON 序列化
    """
    try:
        write = get_stream_writer()
        write({"event": event_type, "data": data})
    except Exception:
        # 若在非流式上下文（如单元测试）中调用，静默忽略
        pass
