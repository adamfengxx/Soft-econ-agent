### Overview

EconAgent is a multi-agent AI system designed for global macroeconomic research. 
Users submit a natural language query such as "Compare China and US GDP growth from 2020 to 2024"
and the system autonomously decomposes the request into a dependency-ordered task plan, retrieves data from authoritative external sources, 
and streams a structured research report back to the user in real time.

The system is built on LangGraph, a stateful graph execution framework that orchestrates four specialized agent nodes:

1. **Taker** — classifies user intent (simple_chat vs complex_research) and infers the desired response format (brief vs detailed) using structured LLM output
2. **Planner** — decomposes the research question into a DAG (directed acyclic graph) of subtasks, where each task declares explicit dependencies on prior tasks
3. **Coordinator** — schedules task execution by selecting the next subtask whose dependencies have been satisfied
4. **Worker** — executes a single subtask via an agentic tool-calling loop: the LLM iteratively calls external data APIs until it has sufficient information to produce a result
5. **Writer** — synthesizes all task results into a final response, applying the appropriate format based on the inferred response style

### Data resource and tools

We use different official data resource combined with the real-time web search to cover the majority of requests the user may be interested in.

| Tool | Capacity |
|---|---|
| **World Bank**| 150+ countries, major macro indicators |
| **IMF** | Balance of payments, fiscal data |
| **OECD** | Developed economy statistics |
| **Eurostat** | EU regional data |
| **Federal Reserve (FRED)** | US macroeconomic series, frequently updated |
| **Alpha Vantage** | US macroeconomic series, frequently updated |
| **Brave Search** | Live web search for news and recent policy data |
| **python_calculator(local)** | Arithmetic and derived metric computation |


### What Does the System Do?

Users ask questions in natural language (e.g., “Compare GDP growth rates in China and the U.S. from 2020 to 2024”), and the system automatically:

1. **Intent Recognition**: Is it a simple greeting or a request for data analysis?
2. **Task Decomposition**: Breaks down the main question into multiple subtasks (e.g., “Look up China's GDP,” “Look up the U.S.'s GDP,” “Compare and analyze”)
3. **Execute Based on Dependencies**: Tasks with sequential dependencies are executed in order, with each task calling real external APIs to retrieve data
4. **Streaming Output**: Use SSE to push real-time progress updates to the frontend throughout the process (“Querying...” or “Task completed...”)
5. **Generate Report**: Aggregate all data and output a concise answer or a comprehensive research report based on user requirements

### Architecture of the system
```
User browser
    │ HTTP POST /api/chat (with JWT token)
    ▼
FastAPI (routes_chat.py)
    │ Parse request, authenticate JWT, load history summary from DB
    ▼
LangGraph StateGraph (graph execution engine)
    │
    ├── Taker node (intent classification)
    │     └── classify_intent() → OpenAI structured output
    │
    ├── [Simple Question] → SimpleChat node → Stream text output → END
    │
    └── [Research Question] → Planner node (task planning)
                         │ plan_tasks() → OpenAI structured output → Task list
                         ▼
                   Coordinator node (Select next task)
                         │ Find the first task with “dependencies satisfied and not yet completed”
                         ▼
                   Worker node (Execute task)
                         │ Tool calling loop: Call APIs for the World Bank, IMF, FRED, etc.
                         │ ← Loop until no more tools to call
                         ▼
                   check_progress()
                         ├── Tasks remaining → Back to Coordinator
                         └── All completed → Writer node
                                           │ Aggregate all task results
                                           └── Stream-process the final report → END
    │
    ▼ SSE event stream (each node emits via `emit_sse()` → forwarded by API layer)
Real-time display in user browser
```
## Deployment ##
The full stack — PostgreSQL, FastAPI backend, and React/Vite frontend served via nginx — is containerized with Docker Compose. 
The frontend build is a standard two-stage Docker build: Node compiles the static assets, 
which are then served by nginx with /api/* reverse-proxied to the backend. SSE streaming requires nginx buffering to be explicitly disabled.
