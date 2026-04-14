"""
GET  /api/threads        — 获取用户的所有对话线程列表。
DELETE /api/threads/{id} — 删除指定线程及其消息。
"""
from fastapi import APIRouter, Depends, HTTPException, Request

from app.db.repositories import thread as thread_repo
from app.services.auth import get_current_user_id

router = APIRouter()


@router.get("/api/threads")
async def list_threads(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """
    返回指定用户的线程列表（按最近更新倒序）。

    Response:
    {
        "threads": [
            {
                "id": "...",
                "title": "...",
                "message_count": 10,
                "updated_at": "2024-01-01T00:00:00+00:00"
            },
            ...
        ]
    }
    """
    pool = request.app.state.db_pool
    threads = await thread_repo.list_threads_for_user(user_id, pool)

    return {
        "threads": [
            {
                "id": t["id"],
                "title": t["title"],
                "message_count": t["message_count"],
                "updated_at": t["updated_at"].isoformat(),
            }
            for t in threads
        ]
    }


@router.delete("/api/threads/{thread_id}")
async def delete_thread(
    thread_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """删除指定线程及其所有消息。"""
    pool = request.app.state.db_pool
    deleted = await thread_repo.delete_thread(thread_id, pool)
    if not deleted:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"ok": True}
