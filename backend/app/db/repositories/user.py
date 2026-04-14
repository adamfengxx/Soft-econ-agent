"""
User 仓库：users 表的认证相关操作。
"""
from uuid import uuid4

import asyncpg


async def create_user(email: str, password_hash: str, pool: asyncpg.Pool) -> dict | None:
    """
    注册新用户。邮箱已存在时返回 None。
    """
    user_id = str(uuid4())
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO users(id, email, password_hash)
            VALUES($1, $2, $3)
            ON CONFLICT (email) DO NOTHING
            RETURNING id, email, created_at
            """,
            user_id, email, password_hash,
        )
        return dict(row) if row else None


async def get_user_by_email(email: str, pool: asyncpg.Pool) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, password_hash, created_at FROM users WHERE email = $1",
            email,
        )
        return dict(row) if row else None


async def get_user_by_id(user_id: str, pool: asyncpg.Pool) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, created_at FROM users WHERE id = $1",
            user_id,
        )
        return dict(row) if row else None
