"""
Message 仓库：messages 表的 CRUD 操作。
"""
from uuid import uuid4

import asyncpg


async def save_message(
    thread_id: str,
    role: str,
    content: str,
    pool: asyncpg.Pool,
) -> dict:
    """持久化一条消息，返回插入的行。"""
    msg_id = str(uuid4())
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO messages(id, thread_id, role, content)
            VALUES($1, $2, $3, $4)
            RETURNING *
            """,
            msg_id,
            thread_id,
            role,
            content,
        )
        return dict(row)


async def get_messages(
    thread_id: str,
    pool: asyncpg.Pool,
) -> list[dict]:
    """按时间顺序返回线程的全部消息。"""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, thread_id, role, content, created_at
            FROM messages
            WHERE thread_id = $1
            ORDER BY created_at ASC
            """,
            thread_id,
        )
        return [dict(r) for r in rows]
