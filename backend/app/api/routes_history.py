"""
GET /api/history/{thread_id} — 获取线程的完整消息历史（从 DB，非 LangGraph checkpointer）。
"""
from fastapi import APIRouter, Depends, Request

from app.db.repositories import message as message_repo
from app.db.repositories import thread as thread_repo
from app.services.auth import get_current_user_id

router = APIRouter()


@router.get("/api/history/{thread_id}")
async def get_history(
    thread_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """
    返回指定线程的消息列表和摘要。

    Response:
    {
        "thread_id": "...",
        "title": "...",
        "summary": "...",
        "messages": [{"role": "user"|"assistant", "content": "...", "created_at": "..."}, ...]
    }
    """
    pool = request.app.state.db_pool
    thread = await thread_repo.get_thread(thread_id, pool)
    messages = await message_repo.get_messages(thread_id, pool)

    return {
        "thread_id": thread_id,
        "title": thread["title"] if thread else None,
        "summary": thread["summary"] if thread else None,
        "messages": [
            {
                "role": m["role"],
                "content": m["content"],
                "created_at": m["created_at"].isoformat(),
            }
            for m in messages
        ],
    }
