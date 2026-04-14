import json
from datetime import date

import httpx
from langchain_core.tools import tool

from app.config import settings


@tool
async def alpha_vantage_api(
    function: str,
    symbol: str = "",
    interval: str = "annual",
) -> str:
    """
    从 Alpha Vantage 获取实时或近期宏观经济与金融数据。
    数据更新比 World Bank / IMF 快 6-12 个月，适合查询最近 1-2 年的数据。
    需要在 .env 中配置 ALPHA_VANTAGE_API_KEY（免费申请：https://www.alphavantage.co/support/#api-key）

    Args:
        function: 数据类型，常用值:
            宏观经济（无需 symbol）:
            - REAL_GDP              → 美国实际 GDP（季度/年度）
            - REAL_GDP_PER_CAPITA   → 美国人均实际 GDP
            - TREASURY_YIELD        → 美国国债收益率
            - FEDERAL_FUNDS_RATE    → 美国联邦基金利率
            - CPI                   → 美国 CPI 通胀
            - INFLATION             → 美国通胀率（年度）
            - RETAIL_SALES          → 美国零售额
            - UNEMPLOYMENT          → 美国失业率
            - NONFARM_PAYROLL        → 美国非农就业
            汇率（需要 symbol，格式 "USD/CNY"）:
            - CURRENCY_EXCHANGE_RATE → 实时汇率
            大宗商品（无需 symbol）:
            - WTI                   → 原油价格 (WTI)
            - BRENT                 → 原油价格 (Brent)
            - NATURAL_GAS           → 天然气价格
            - COPPER / ALUMINUM / WHEAT / CORN / COTTON / SUGAR / COFFEE
        symbol: 汇率时填货币对，如 "USD/CNY"、"EUR/USD"；其他情况留空
        interval: "annual"（年度）或 "monthly"（月度），宏观指标适用
    """
    if not settings.ALPHA_VANTAGE_API_KEY:
        return "[alpha_vantage_api] ALPHA_VANTAGE_API_KEY not configured. Get a free key at https://www.alphavantage.co/support/#api-key"

    params: dict = {
        "function": function,
        "apikey": settings.ALPHA_VANTAGE_API_KEY,
    }
    if interval and function not in ("CURRENCY_EXCHANGE_RATE",):
        params["interval"] = interval
    if symbol:
        if function == "CURRENCY_EXCHANGE_RATE":
            parts = symbol.split("/")
            if len(parts) == 2:
                params["from_currency"] = parts[0].strip()
                params["to_currency"] = parts[1].strip()
        else:
            params["symbol"] = symbol

    url = "https://www.alphavantage.co/query"
    async with httpx.AsyncClient(timeout=settings.TOOL_CALL_TIMEOUT) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    # Error handling
    if "Error Message" in data:
        return f"[Alpha Vantage] Error: {data['Error Message']}"
    if "Information" in data:
        return f"[Alpha Vantage] API limit reached: {data['Information']}"
    if "Note" in data:
        return f"[Alpha Vantage] Note: {data['Note']}"

    # Exchange rate — return directly
    if function == "CURRENCY_EXCHANGE_RATE":
        info = data.get("Realtime Currency Exchange Rate", {})
        return json.dumps({
            "from": info.get("1. From_Currency Code"),
            "to": info.get("3. To_Currency Code"),
            "rate": info.get("5. Exchange Rate"),
            "last_refreshed": info.get("6. Last Refreshed"),
        }, ensure_ascii=False)

    # Commodity / macro time series
    records = data.get("data", [])
    if not records:
        return f"No Alpha Vantage data returned for function={function}."

    # Return latest 10 data points
    today = date.today().isoformat()
    recent = [r for r in records if r.get("date", "") <= today][:10]
    return json.dumps(recent, ensure_ascii=False)
