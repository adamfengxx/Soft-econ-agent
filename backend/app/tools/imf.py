import json
from datetime import date

import httpx
from langchain_core.tools import tool

from app.config import settings


@tool
async def imf_data_api(
    dataset: str,
    country_code: str,
    indicator: str,
    start_year: int = 2018,
    end_year: int | None = None,
) -> str:
    """
    从 IMF Data API 获取宏观经济数据。

    Args:
        dataset: 数据集代码 (如 "WEO" World Economic Outlook,
                 "IFS" International Financial Statistics) — 注：当前实现使用 DataMapper API，
                 dataset 参数保留供描述用途
        country_code: ISO 国家代码 (如 CHN, USA, JPN)
        indicator: 指标代码，常用值:
            - NGDP_RPCH   (Real GDP growth %)
            - PCPIPCH     (Inflation, average consumer prices %)
            - BCA_NGDPD   (Current account balance % of GDP)
            - LUR         (Unemployment rate %)
            - GGXWDG_NGDP (Gross government debt % of GDP)
        start_year: 起始年份
        end_year: 结束年份
    """
    if end_year is None:
        end_year = date.today().year
    url = (
        f"https://www.imf.org/external/datamapper/api/v2"
        f"/{indicator}/{country_code}"
    )
    async with httpx.AsyncClient(timeout=settings.TOOL_CALL_TIMEOUT) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    values = (
        data.get("values", {})
        .get(indicator, {})
        .get(country_code, {})
    )

    if not values:
        return f"No IMF data found for {country_code} / {indicator}."

    filtered = {
        y: v
        for y, v in values.items()
        if start_year <= int(y) <= end_year
    }

    if not filtered:
        return f"IMF data exists for {country_code} / {indicator} but not in range {start_year}-{end_year}."

    return json.dumps(filtered, ensure_ascii=False)
