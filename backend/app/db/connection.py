"""
asyncpg 连接池管理。

使用 asyncpg 而非 psycopg3 pool（asyncpg 已在 requirements 中，且无需额外安装 psycopg_pool）。
启动时调用 create_pool()，关闭时调用 close_pool()。
"""
import logging

import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None

# ── Schema（幂等，每次启动时执行）────────────────────────────────────────────
_SCHEMA_SQL = """
-- 注册用户
CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    email         TEXT UNIQUE,
    password_hash TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 兼容升级：旧表可能没有 email / password_hash 列
ALTER TABLE users ADD COLUMN IF NOT EXISTS email         TEXT UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT;

-- 对话线程
CREATE TABLE IF NOT EXISTS threads (
    id              TEXT PRIMARY KEY,        -- 与 LangGraph thread_id 相同
    user_id         TEXT NOT NULL REFERENCES users(id),
    title           TEXT,                    -- 自动取第一条用户消息前 60 字
    summary         TEXT,                    -- 历史摘要缓存
    summary_up_to   INT NOT NULL DEFAULT 0,  -- 生成摘要时的 message_count
    message_count   INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_threads_user
    ON threads(user_id, updated_at DESC);

-- 消息记录（持久化历史，独立于 LangGraph checkpointer）
CREATE TABLE IF NOT EXISTS messages (
    id          TEXT PRIMARY KEY,
    thread_id   TEXT NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_thread
    ON messages(thread_id, created_at);
"""


def _to_asyncpg_dsn(url: str) -> str:
    """将 psycopg3 格式的 DSN 转为 asyncpg 兼容格式。"""
    return url.replace("postgresql+psycopg://", "postgresql://")


async def create_pool() -> asyncpg.Pool:
    global _pool
    _pool = await asyncpg.create_pool(
        dsn=_to_asyncpg_dsn(settings.DATABASE_URL),
        min_size=2,
        max_size=10,
        command_timeout=60,
    )
    logger.info("asyncpg pool created")
    return _pool


async def apply_schema(pool: asyncpg.Pool) -> None:
    """幂等建表：每次启动时执行，已存在则跳过。"""
    async with pool.acquire() as conn:
        await conn.execute(_SCHEMA_SQL)
    logger.info("DB schema applied")


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB pool not initialized. Call create_pool() first.")
    return _pool


async def close_pool() -> None:
    if _pool:
        await _pool.close()
        logger.info("asyncpg pool closed")
