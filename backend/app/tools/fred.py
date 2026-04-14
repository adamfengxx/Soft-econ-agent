import json
from datetime import date

import httpx
from langchain_core.tools import tool

from app.config import settings


@tool
async def fred_api(
    series_id: str,
    start_date: str = "2018-01-01",
    end_date: str | None = None,
    frequency: str = "a",
) -> str:
    """
    从 FRED (Federal Reserve Economic Data) 获取美国及全球宏观经济数据。
    需要在 .env 中配置 FRED_API_KEY（免费申请：https://fred.stlouisfed.org/docs/api/api_key.html）

    Args:
        series_id: FRED 指标代码，常用值:
            美国宏观:
            - GDP          (US GDP, Billions of Dollars)
            - GDPC1        (Real US GDP, Chained 2017 Dollars)
            - CPIAUCSL      (CPI — All Urban Consumers)
            - UNRATE        (US Unemployment Rate %)
            - FEDFUNDS      (Federal Funds Effective Rate %)
            - DGS10         (10-Year Treasury Constant Maturity Rate)
            - M2SL          (M2 Money Supply)
            - BAMLH0A0HYM2  (High Yield Bond Spread)
            - DEXUSEU       (USD/EUR Exchange Rate)
            - DEXCHUS       (USD/CNY Exchange Rate)
            - HOUST         (Housing Starts)
            - INDPRO        (Industrial Production Index)
            全球数据:
            - CHNGDPNQDSMEI (China GDP)
            - JPNRGDPEXP    (Japan Real GDP)
        start_date: 起始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        frequency: 数据频率:
            - a  (Annual — 年度)
            - q  (Quarterly — 季度)
            - m  (Monthly — 月度)
            - w  (Weekly — 周度)
            - d  (Daily — 日度)
    """
    if end_date is None:
        end_date = date.today().isoformat()
    if not settings.FRED_API_KEY:
        return "[fred_api] FRED_API_KEY not configured. Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html"

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": settings.FRED_API_KEY,
        "file_type": "json",
        "observation_start": start_date,
        "observation_end": end_date,
        "frequency": frequency,
    }

    async with httpx.AsyncClient(timeout=settings.TOOL_CALL_TIMEOUT) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    observations = data.get("observations", [])
    if not observations:
        return f"No FRED data found for series '{series_id}' ({start_date} to {end_date})."

    records = [
        {"date": obs["date"], "value": obs["value"]}
        for obs in observations
        if obs["value"] != "."  # FRED uses "." for missing values
    ]

    if not records:
        return f"FRED series '{series_id}' exists but all values are missing in this range."

    return json.dumps(records, ensure_ascii=False)
