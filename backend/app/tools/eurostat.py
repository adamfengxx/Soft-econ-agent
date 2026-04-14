import json
from datetime import date

import httpx
from langchain_core.tools import tool

from app.config import settings


@tool
async def eurostat_api(
    dataset: str,
    geo: str = "",
    start_year: int = 2018,
    end_year: int | None = None,
) -> str:
    """
    从 Eurostat REST API 获取欧洲统计数据。无需 API Key。

    Args:
        dataset: Eurostat 数据集代码，常用值:
            - nama_10_gdp      (GDP and main components — 国民账户)
            - prc_hicp_aind    (HICP — 欧元区通货膨胀)
            - une_rt_a         (Unemployment rate, annual)
            - gov_10a_main     (Government deficit and debt)
            - ext_lt_mainbalance (EU trade balance)
            - demo_gind         (Population indicators)
        geo: 国家/地区代码，多个用逗号分隔 (如 "DE,FR,IT,ES")
            EU 整体用 "EU27_2020"，欧元区用 "EA20"
            常用: DE(德国), FR(法国), IT(意大利), ES(西班牙), NL(荷兰), PL(波兰)
        start_year: 起始年份
        end_year: 结束年份
    """
    if end_year is None:
        end_year = date.today().year
    params: dict = {
        "format": "JSON",
        "lang": "EN",
        "sinceTimePeriod": str(start_year),
        "untilTimePeriod": str(end_year),
    }
    if geo:
        params["geo"] = geo

    url = f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}"

    async with httpx.AsyncClient(timeout=settings.TOOL_CALL_TIMEOUT) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    # Parse Eurostat JSON-stat format
    try:
        dims = data["dimension"]
        time_dim = dims.get("time", {})
        geo_dim = dims.get("geo", {})
        values = data["value"]

        time_labels = list(time_dim.get("category", {}).get("label", {}).values())
        geo_labels = list(geo_dim.get("category", {}).get("label", {}).values())
        geo_ids = list(geo_dim.get("category", {}).get("index", {}).keys())

        if not values:
            return f"No Eurostat data found for {dataset} ({start_year}-{end_year})."

        records = []
        n_time = len(time_labels)
        for idx_str, val in values.items():
            idx = int(idx_str)
            geo_i = idx // n_time
            time_i = idx % n_time
            records.append({
                "geo": geo_ids[geo_i] if geo_i < len(geo_ids) else str(geo_i),
                "geo_label": geo_labels[geo_i] if geo_i < len(geo_labels) else "",
                "time": time_labels[time_i] if time_i < len(time_labels) else str(time_i),
                "value": val,
            })

        return json.dumps(records[:100], ensure_ascii=False)
    except (KeyError, IndexError) as e:
        return f"[Eurostat] Failed to parse response: {e}"
