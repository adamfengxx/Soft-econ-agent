import json

import httpx
from langchain_core.tools import tool

from app.config import settings


@tool
async def brave_search(query: str, count: int = 5) -> str:
    """
    使用 Brave Search API 搜索最新网络信息。
    适用于获取新闻、政策变动、市场分析等实时信息。

    Args:
        query: 搜索关键词（英文效果更佳）
        count: 返回结果数量 (1-10)
    """
    if not settings.BRAVE_API_KEY:
        return "[brave_search] BRAVE_API_KEY not configured. Skipping web search."

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "X-Subscription-Token": settings.BRAVE_API_KEY,
        "Accept": "application/json",
    }
    params = {"q": query, "count": min(count, 10)}

    async with httpx.AsyncClient(timeout=settings.TOOL_CALL_TIMEOUT) as client:
        resp = await client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

    results = [
        {
            "title": item["title"],
            "url": item["url"],
            "snippet": item.get("description", ""),
        }
        for item in data.get("web", {}).get("results", [])
    ]

    if not results:
        return f"No web results found for: {query}"

    return json.dumps(results, ensure_ascii=False)
