import json
from datetime import date

import httpx
from langchain_core.tools import tool

from app.config import settings


@tool
async def oecd_api(
    dataset: str,
    countries: str,
    indicator: str,
    start_year: int = 2018,
    end_year: int | None = None,
) -> str:
    """
    从 OECD Data API 获取经济统计数据。无需 API Key。

    Args:
        dataset: 数据集代码，常用值:
            - QNA          (Quarterly National Accounts — GDP)
            - KEI          (Key Economic Indicators)
            - MEI          (Main Economic Indicators)
            - HEALTH_STAT  (Health Statistics)
            - EO           (Economic Outlook)
        countries: 国家代码，多国用"+"连接 (如 "USA+GBR+DEU+JPN")
            使用 OECD 格式: USA, GBR, DEU, FRA, JPN, CHN, KOR, AUS, CAN, ITA
        indicator: 指标代码，例如:
            - B1_GE        (GDP, expenditure approach)
            - P31S14_S15   (Household consumption)
            - P5            (Gross capital formation)
            - B6G            (Current account balance)
            - CPALTT01      (CPI, total)
            - LRHUTTTT      (Unemployment rate)
        start_year: 起始年份
        end_year: 结束年份
    """
    if end_year is None:
        end_year = date.today().year
    url = (
        f"https://stats.oecd.org/SDMX-JSON/data/{dataset}/"
        f"{indicator}.{countries}.A/"
        f"all?startTime={start_year}&endTime={end_year}&dimensionAtObservation=allDimensions"
    )
    async with httpx.AsyncClient(timeout=settings.TOOL_CALL_TIMEOUT) as client:
        resp = await client.get(url, headers={"Accept": "application/json"})
        resp.raise_for_status()
        data = resp.json()

    # Parse SDMX-JSON structure
    try:
        structure = data["structure"]
        dims = structure["dimensions"]["observation"]
        dim_map = {d["id"]: {str(i): v["id"] for i, v in enumerate(d["values"])} for d in dims}

        observations = data["dataSets"][0]["observations"]
        records = []
        for key, val_list in observations.items():
            indices = key.split(":")
            row = {d["id"]: dim_map[d["id"]].get(indices[i], indices[i]) for i, d in enumerate(dims)}
            row["value"] = val_list[0]
            records.append(row)

        if not records:
            return f"No OECD data found for {dataset}/{indicator}/{countries} ({start_year}-{end_year})."

        return json.dumps(records[:100], ensure_ascii=False)  # cap at 100 rows
    except (KeyError, IndexError) as e:
        return f"[OECD] Failed to parse response: {e}"
