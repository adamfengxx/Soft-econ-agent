import json
from datetime import date

import httpx
from langchain_core.tools import tool

from app.config import settings


@tool
async def world_bank_api(
    country_code: str,
    indicator: str,
    start_year: int = 2018,
    end_year: int | None = None,
) -> str:
    """
    从世界银行 API 获取经济指标数据。

    Args:
        country_code: ISO 3166-1 国家代码 (如 CHN, USA, JPN, DEU)
        indicator: 世界银行指标代码，常用值:
            - NY.GDP.MKTP.CD     (GDP, current US$)
            - NY.GDP.PCAP.CD     (GDP per capita, current US$)
            - NY.GDP.MKTP.KD.ZG  (GDP growth rate, annual %)
            - SL.UEM.TOTL.ZS     (Unemployment rate %)
            - FP.CPI.TOTL.ZG     (Inflation, CPI %)
            - NE.EXP.GNFS.CD     (Exports of goods and services)
            - NE.IMP.GNFS.CD     (Imports of goods and services)
        start_year: 起始年份
        end_year: 结束年份
    """
    if end_year is None:
        end_year = date.today().year
    url = (
        f"https://api.worldbank.org/v2/country/{country_code}" #网站更新，之前是v1，现在是v2
        f"/indicator/{indicator}"
        f"?date={start_year}:{end_year}&format=json&per_page=100"
    )
    async with httpx.AsyncClient(timeout=settings.TOOL_CALL_TIMEOUT) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    if len(data) < 2 or not data[1]:
        return f"No data found for {country_code} / {indicator} ({start_year}-{end_year})."

    records = [
        {"year": item["date"], "value": item["value"]}
        for item in data[1]
        if item["value"] is not None
    ]

    if not records:
        return f"Data exists but all values are null for {country_code} / {indicator}."

    return json.dumps(records, ensure_ascii=False)
