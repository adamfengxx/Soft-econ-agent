"""
FastAPI 应用入口。

启动顺序：
  1. 创建 asyncpg 连接池，执行幂等建表 SQL
  2. 编译 LangGraph 图，连接 PostgreSQL checkpointer

关闭顺序：
  1. 关闭 asyncpg 连接池
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_auth import router as auth_router
from app.api.routes_chat import router as chat_router
from app.api.routes_history import router as history_router
from app.api.routes_threads import router as threads_router
from app.db.connection import apply_schema, close_pool, create_pool
from app.graph.builder import get_compiled_graph
from app.services.checkpointer import get_checkpointer_context


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── 启动 ──────────────────────────────────────────────────────────────────
    # 1. DB 连接池 + 幂等建表
    pool = await create_pool()
    await apply_schema(pool)
    app.state.db_pool = pool

    # 2. LangGraph checkpointer（需在整个 app 生命周期内保持连接）
    async with get_checkpointer_context() as checkpointer:
        await checkpointer.setup()
        app.state.graph = get_compiled_graph(checkpointer)

        yield

    # ── 关闭 ──────────────────────────────────────────────────────────────────
    await close_pool()


app = FastAPI(
    title="EconAgent",
    description="基于 LangGraph 多智能体的全球经济研究系统",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 生产环境请改为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(history_router)
app.include_router(threads_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
