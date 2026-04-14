"""
Thread 仓库：threads 表的 CRUD 操作。
"""
from uuid import uuid4

import asyncpg


async def get_or_create_thread(
    thread_id: str,
    user_id: str,
    pool: asyncpg.Pool,
) -> dict:
    """
    确保 user 和 thread 存在于数据库中（upsert）。
    线程已存在时直接返回，不覆盖任何字段。
    """
    async with pool.acquire() as conn:
        # 幂等写入用户
        await conn.execute(
            "INSERT INTO users(id) VALUES($1) ON CONFLICT DO NOTHING",
            user_id,
        )
        # 幂等写入线程
        await conn.execute(
            """
            INSERT INTO threads(id, user_id)
            VALUES($1, $2)
            ON CONFLICT (id) DO NOTHING
            """,
            thread_id,
            user_id,
        )
        row = await conn.fetchrow("SELECT * FROM threads WHERE id = $1", thread_id)
        return dict(row)


async def get_thread(thread_id: str, pool: asyncpg.Pool) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM threads WHERE id = $1", thread_id)
        return dict(row) if row else None


async def set_title_if_empty(
    thread_id: str,
    title: str,
    pool: asyncpg.Pool,
) -> None:
    """仅在 title 为 NULL 时设置（首条消息自动命名）。"""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE threads
            SET title = $2
            WHERE id = $1 AND title IS NULL
            """,
            thread_id,
            title[:60],
        )


async def increment_message_count(thread_id: str, pool: asyncpg.Pool) -> int:
    """将 message_count +1，返回更新后的值。"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE threads
            SET message_count = message_count + 1,
                updated_at    = NOW()
            WHERE id = $1
            RETURNING message_count
            """,
            thread_id,
        )
        return row["message_count"] if row else 0


async def update_summary(
    thread_id: str,
    summary: str,
    summary_up_to: int,
    pool: asyncpg.Pool,
) -> None:
    """更新压缩摘要及摘要覆盖到的消息数。"""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE threads
            SET summary       = $2,
                summary_up_to = $3,
                updated_at    = NOW()
            WHERE id = $1
            """,
            thread_id,
            summary,
            summary_up_to,
        )


async def delete_thread(thread_id: str, pool: asyncpg.Pool) -> bool:
    """删除指定线程及其所有消息（依赖 CASCADE）。返回是否找到并删除。"""
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM threads WHERE id = $1",
            thread_id,
        )
        return result == "DELETE 1"


async def list_threads_for_user(
    user_id: str,
    pool: asyncpg.Pool,
    limit: int = 50,
) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, title, summary, message_count, created_at, updated_at
            FROM threads
            WHERE user_id = $1
            ORDER BY updated_at DESC
            LIMIT $2
            """,
            user_id,
            limit,
        )
        return [dict(r) for r in rows]
