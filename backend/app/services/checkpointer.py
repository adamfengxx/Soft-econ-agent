"""
PostgreSQL Checkpointer 初始化。

LangGraph 用 checkpointer 做图状态持久化，支持多轮对话记忆。
"""
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config import settings


def get_checkpointer_context():
    """
    返回 AsyncPostgresSaver 的异步上下文管理器。

    用法（在 lifespan 中）:
        async with get_checkpointer_context() as checkpointer:
            await checkpointer.setup()
            ...
    """
    # AsyncPostgresSaver 使用 psycopg3，DSN 不含 +psycopg 前缀
    dsn = settings.DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")
    return AsyncPostgresSaver.from_conn_string(dsn)
