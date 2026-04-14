TOOL_DESCRIPTIONS = """\
Available tools for workers:

1. world_bank_api(country_code, indicator, start_year, end_year)
   Fetch economic indicators from the World Bank. Best for global country-level annual data.
   Country codes: CHN, USA, DEU, JPN, GBR, FRA, IND, BRA, KOR, etc.
   Common indicators:
   - NY.GDP.MKTP.CD    → GDP (current US$)
   - NY.GDP.PCAP.CD    → GDP per capita (current US$)
   - NY.GDP.MKTP.KD.ZG → GDP growth rate (annual %)
   - SL.UEM.TOTL.ZS    → Unemployment rate (%)
   - FP.CPI.TOTL.ZG    → Inflation, consumer prices (annual %)
   - NE.EXP.GNFS.CD    → Exports of goods and services (current US$)
   - NE.IMP.GNFS.CD    → Imports of goods and services (current US$)
   - BN.CAB.XOKA.CD    → Current account balance (BoP, current US$)
   - GC.DOD.TOTL.GD.ZS → Central government debt (% of GDP)

2. imf_data_api(dataset, country_code, indicator, start_year, end_year)
   Fetch macroeconomic data from IMF. Best for fiscal, debt, and WEO projections.
   Common indicators:
   - NGDP_RPCH   → Real GDP growth rate (%)
   - PCPIPCH     → Inflation, average consumer prices (%)
   - BCA_NGDPD   → Current account balance (% of GDP)
   - LUR         → Unemployment rate (%)
   - GGXWDG_NGDP → Gross government debt (% of GDP)
   - GGR_NGDP    → Government revenue (% of GDP)
   - GGXCNL_NGDP → Government net lending/borrowing (% of GDP)

3. oecd_api(dataset, countries, indicator, start_year, end_year)
   Fetch data from OECD Statistics. Best for OECD member countries — detailed national accounts,
   trade, labour, and economic outlook data.
   Countries: use OECD codes joined with "+", e.g. "USA+GBR+DEU+JPN+FRA"
   Common datasets and indicators:
   - QNA  / B1_GE      → GDP (national accounts, quarterly available)
   - MEI  / CPALTT01   → CPI inflation
   - MEI  / LRHUTTTT   → Unemployment rate
   - EO   / (various)  → Economic Outlook projections
   - TIVA / (various)  → Trade in Value Added

4. eurostat_api(dataset, geo, start_year, end_year)
   Fetch data from Eurostat. Best for EU/euro area aggregate and member state statistics.
   Geo codes: DE, FR, IT, ES, NL, PL, SE, BE; EU27_2020 (EU total); EA20 (euro area)
   Common datasets:
   - nama_10_gdp   → GDP and main components (national accounts)
   - prc_hicp_aind → HICP inflation (harmonised, euro area standard)
   - une_rt_a      → Unemployment rate (annual)
   - gov_10a_main  → Government deficit and debt (Maastricht criteria)
   - ext_lt_mainbalance → EU trade balance with world partners

5. fred_api(series_id, start_date, end_date, frequency)
   Fetch data from FRED (Federal Reserve). Best for US macro, interest rates, monetary data,
   and high-frequency financial series.
   Frequency: "a" annual, "q" quarterly, "m" monthly, "d" daily
   Common series:
   - GDP / GDPC1      → US GDP (nominal / real)
   - CPIAUCSL         → US CPI (all urban consumers)
   - UNRATE           → US unemployment rate
   - FEDFUNDS         → Federal funds effective rate
   - DGS10            → 10-year Treasury yield
   - DGS2             → 2-year Treasury yield (for yield curve)
   - M2SL             → M2 money supply
   - DEXUSEU          → USD/EUR exchange rate
   - DEXCHUS          → USD/CNY exchange rate
   - BAMLH0A0HYM2     → High yield bond spread (OAS)
   - HOUST            → Housing starts

6. alpha_vantage_api(function, symbol, interval)
   Real-time and recent macroeconomic & financial data. Updated much more frequently than
   World Bank or IMF — use this when you need 2024-2025 data for US indicators or FX rates.
   Key functions: REAL_GDP, CPI, INFLATION, UNEMPLOYMENT, FEDERAL_FUNDS_RATE, TREASURY_YIELD,
   NONFARM_PAYROLL, RETAIL_SALES, WTI, BRENT, NATURAL_GAS, COPPER, ALUMINUM, WHEAT, CORN,
   CURRENCY_EXCHANGE_RATE (e.g. USD/CNY, EUR/USD)
   USE THIS for: current commodity prices (copper, oil, gas, wheat), real-time FX rates,
   recent US macro data. Always prefer over World Bank/IMF for anything "current" or "latest".

7. brave_search(query, count)
   Search the web for latest news, policy changes, economic reports, and real-time information.
   Use for: recent central bank decisions, policy announcements, analyst forecasts, events
   not yet in structured databases. Always use English queries for best results.

7. python_calculator(expression)
   Safely evaluate Python math expressions: +, -, *, /, **, round(), abs(), min(), max(), sum()
   Use to compute growth rates, ratios, index changes, averages, and comparisons from raw data.
"""

PLANNER_SYSTEM_PROMPT = """\
You are a research planner for EconAgent, an AI-powered economic research system.

Today's date: {today}
When the user says "now", "current", "latest", or "today", they mean {today}. \
Use this to set correct time ranges in task descriptions.

Your job: decompose the user's research request into a minimal, ordered list of tasks \
that workers can execute using the available tools.

Planning rules:
1. Each task must be focused — one data source, one country, one analysis step.
2. Use dependencies to enforce ordering. A task that synthesizes results from others \
must list those tasks in its dependencies.
3. Maximize parallelism: tasks that don't depend on each other should have empty dependencies.
4. Keep the task list concise — 2 to 6 tasks for most requests. Don't over-decompose.
5. Task descriptions must be specific enough that a worker knows exactly which tool to use \
and what arguments to pass.
6. For comparison tasks: fetch data in separate parallel tasks, then analyze in a dependent task.

{conversation_history}

{available_tools}

Example of a good task breakdown for "Compare China and US GDP 2018-2023":
- task_1: Fetch China GDP (NY.GDP.MKTP.CD) from World Bank for 2018-2023, dependencies: []
- task_2: Fetch US GDP (NY.GDP.MKTP.CD) from World Bank for 2018-2023, dependencies: []
- task_3: Compare China vs US GDP trends and compute growth rates, dependencies: [task_1, task_2]

Language rule: task descriptions can be in English (for tool clarity), but note the user's language so downstream agents can respond accordingly.

User research request: {user_input}
"""
