# EconAgent 后端架构深度解析

> 本文档面向学习目的，逐文件、逐模块详细解释后端每一部分的设计思路与实现细节。

---

## 目录

1. [项目全貌](#1-项目全貌)
2. [启动入口 — main.py](#2-启动入口--mainpy)
3. [配置系统 — config.py](#3-配置系统--configpy)
4. [数据模型 — models/schemas.py](#4-数据模型--modelsschemаspy)
5. [图状态 — graph/state.py](#5-图状态--graphstatepy)
6. [图构建 — graph/builder.py 与 edges.py](#6-图构建--graphbuilderpy-与-edgespy)
7. [节点详解 — graph/nodes/](#7-节点详解--graphnodes)
   - 7.1 Taker — 意图分类
   - 7.2 Planner — 任务规划
   - 7.3 Coordinator — 任务调度
   - 7.4 Worker — 任务执行
   - 7.5 Writer — 报告汇总
   - 7.6 SimpleChat — 简单对话
8. [LLM 层 — llm/](#8-llm-层--llm)
   - 8.1 client.py — LLM 工厂
   - 8.2 output_models.py — 结构化输出模型
   - 8.3 wrapper.py — 高层调用封装
9. [SSE 流式推送 — streaming/sse.py](#9-sse-流式推送--streamingssepy)
10. [外部工具 — tools/](#10-外部工具--tools)
11. [数据库层 — db/](#11-数据库层--db)
    - 11.1 connection.py — 连接池与建表
    - 11.2 repositories/thread.py
    - 11.3 repositories/message.py
    - 11.4 repositories/user.py
12. [服务层 — services/](#12-服务层--services)
    - 12.1 auth.py — JWT 认证
    - 12.2 checkpointer.py — 图状态持久化
    - 12.3 summarization.py — 对话摘要压缩
    - 12.4 memory.py — 历史提取
13. [API 路由 — api/](#13-api-路由--api)
    - 13.1 routes_auth.py
    - 13.2 routes_chat.py（核心）
    - 13.3 routes_history.py
    - 13.4 routes_threads.py
14. [完整数据流追踪](#14-完整数据流追踪)
15. [关键设计决策解释](#15-关键设计决策解释)
16. [快速启动](#16-快速启动)

---

## 1. 项目全貌

### 系统做什么？

用户用自然语言提问（如"比较中美2020-2024年GDP增速"），系统自动：

1. **判断意图**：是简单问候还是需要数据研究？
2. **拆解任务**：把大问题分解成多个子任务（如"查中国GDP"、"查美国GDP"、"对比分析"）
3. **按依赖执行**：有前后依赖关系的任务按顺序执行，每个任务调用真实外部 API 取数据
4. **流式输出**：全程用 SSE 实时推送进度给前端（"正在查询中…"、"任务完成…"）
5. **生成报告**：汇总所有数据，根据用户需求输出简洁回答或完整研究报告

### 技术架构总览

```
用户浏览器
    │ HTTP POST /api/chat（携带 JWT token）
    ▼
FastAPI (routes_chat.py)
    │ 解析请求、验证 JWT、从 DB 加载历史摘要
    ▼
LangGraph StateGraph（图执行引擎）
    │
    ├── Taker 节点（意图分类）
    │     └── classify_intent() → OpenAI structured output
    │
    ├── [简单问题] → SimpleChat 节点 → 流式输出文字 → END
    │
    └── [研究问题] → Planner 节点（任务规划）
                         │ plan_tasks() → OpenAI structured output → Task列表
                         ▼
                   Coordinator 节点（挑选下一任务）
                         │ 找第一个"依赖已满足且未完成"的任务
                         ▼
                   Worker 节点（执行任务）
                         │ tool calling loop：调用世界银行/IMF/FRED等API
                         │ ← 循环直到无工具调用
                         ▼
                   check_progress()
                         ├── 还有任务 → 回到 Coordinator
                         └── 全部完成 → Writer 节点
                                           │ 汇总所有任务结果
                                           └── 流式生成最终报告 → END
    │
    ▼ SSE 事件流（每个节点 emit_sse() → API 层转发）
用户浏览器实时显示
```

### 目录结构

```
backend/app/
├── main.py                    # FastAPI 入口，应用生命周期管理
├── config.py                  # 所有配置项（从 .env 读取）
│
├── api/                       # HTTP 路由层
│   ├── routes_auth.py         # 注册/登录/用户信息
│   ├── routes_chat.py         # 核心：接收消息，运行图，SSE 返回
│   ├── routes_history.py      # 获取对话历史
│   └── routes_threads.py      # 列出/删除对话线程
│
├── graph/                     # LangGraph 图定义
│   ├── state.py               # AgentState：图中流转的所有数据
│   ├── builder.py             # 把节点和边组装成图
│   ├── edges.py               # 条件路由函数
│   └── nodes/                 # 每个 AI 节点的实现
│       ├── taker.py           # 意图分类
│       ├── planner.py         # 任务规划
│       ├── coordinator.py     # 任务调度
│       ├── worker.py          # 任务执行（tool calling）
│       ├── writer.py          # 报告汇总
│       └── simple_chat.py     # 简单对话
│
├── llm/                       # LLM 调用封装
│   ├── client.py              # ChatOpenAI 工厂函数
│   ├── output_models.py       # Pydantic 结构化输出模型
│   └── wrapper.py             # 高层调用（intent分类、任务规划）
│
├── tools/                     # 外部数据工具
│   ├── world_bank.py          # 世界银行 API
│   ├── imf.py                 # IMF 数据 API
│   ├── oecd.py                # OECD 统计 API
│   ├── eurostat.py            # 欧盟统计局 API
│   ├── fred.py                # 美联储经济数据 API
│   ├── alpha_vantage.py       # 实时金融数据 API
│   ├── brave_search.py        # 网页搜索 API
│   └── calculator.py          # 本地数学计算
│
├── prompts/                   # 所有节点的系统提示词
│   ├── taker.py
│   ├── planner.py
│   ├── worker.py
│   ├── writer.py
│   └── simple_chat.py
│
├── models/
│   └── schemas.py             # Task、TaskStatus、SSEEventType 定义
│
├── db/                        # 数据库层
│   ├── connection.py          # asyncpg 连接池、建表 SQL
│   └── repositories/          # 数据访问对象（Repository 模式）
│       ├── thread.py          # threads 表操作
│       ├── message.py         # messages 表操作
│       └── user.py            # users 表操作
│
├── services/                  # 业务服务层
│   ├── auth.py                # JWT 签发/验证、密码哈希
│   ├── checkpointer.py        # LangGraph 图状态持久化
│   ├── summarization.py       # 长对话自动摘要压缩
│   └── memory.py              # 从 checkpointer 提取历史（辅助工具）
│
└── streaming/
    └── sse.py                 # emit_sse()：节点内推送事件的工具函数
```

---

## 2. 启动入口 — main.py

```python
# backend/app/main.py

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── 启动阶段 ──
    pool = await create_pool()      # 1. 建立 asyncpg 数据库连接池
    await apply_schema(pool)        # 2. 幂等建表（已存在则跳过）
    app.state.db_pool = pool        # 3. 把连接池挂到 app.state，供路由层使用

    async with get_checkpointer_context() as checkpointer:  # 4. 初始化 LangGraph checkpointer
        await checkpointer.setup()                           # 5. 建立 checkpointer 所需的表
        app.state.graph = get_compiled_graph(checkpointer)  # 6. 编译图，挂到 app.state

        yield  # ← 应用正常运行期间停在这里

    # ── 关闭阶段 ──
    await close_pool()   # 关闭数据库连接池
```

### 理解 `lifespan`

`lifespan` 是 FastAPI 提供的**应用生命周期管理器**，替代了旧版的 `@app.on_event("startup")`。

- `yield` 之前的代码在**启动时**运行（只运行一次）
- `yield` 之后的代码在**关闭时**运行（用于清理资源）
- `app.state` 是 FastAPI 提供的挂载共享对象的地方，所有请求处理函数都能通过 `request.app.state.xxx` 访问

### 为什么 checkpointer 用 `async with`？

LangGraph 的 `AsyncPostgresSaver` 内部持有一个长连接（psycopg3），需要在整个应用生命周期内保持打开。`async with` 保证了：进入时建连接，退出时关连接，不会泄漏。

### 路由注册

```python
app.include_router(auth_router)     # /api/auth/*
app.include_router(chat_router)     # /api/chat
app.include_router(history_router)  # /api/history/*
app.include_router(threads_router)  # /api/threads/*
```

---

## 3. 配置系统 — config.py

```python
# backend/app/config.py

load_dotenv()  # 把 .env 文件写入 os.environ

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    DATABASE_URL: str          # postgresql+psycopg://user:pass@host/db
    BRAVE_API_KEY: str = ""    # 可选，不填时网页搜索会跳过
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 72
    FRED_API_KEY: str = ""
    ALPHA_VANTAGE_API_KEY: str = ""
    MODEL_NAME: str = "gpt-4o"
    MAX_TOOL_ROUNDS: int = 5      # worker 最多调用工具几轮
    TOOL_CALL_TIMEOUT: int = 30   # 单个工具调用超时（秒）
    LLM_CALL_TIMEOUT: int = 180   # LLM 调用超时（秒）
    MAX_TOOL_OUTPUT_TO_LLM: int = 3000  # 工具输出截断长度（避免超出 context）
    SUMMARIZE_THRESHOLD: int = 10  # 累积多少条新消息后触发摘要压缩

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()  # 模块级单例，整个应用共用
```

### 关键设计点

**为什么同时用 `load_dotenv()` 和 `BaseSettings`？**

- `BaseSettings` 从环境变量读配置，类型安全、有默认值
- 问题：`pydantic-settings` 只把环境变量读入 Python 对象，不写回 `os.environ`
- OpenAI SDK 等第三方库直接读 `os.environ["OPENAI_API_KEY"]`，读不到
- 解决方案：在最前面 `load_dotenv()`，把 `.env` 写入 `os.environ`，让所有人都能读到

**`@lru_cache` 的作用**

`lru_cache` 让 `get_settings()` 只执行一次（第一次调用时），之后都返回缓存结果。这样整个应用只有一个 `Settings` 实例，避免重复读文件。

---

## 4. 数据模型 — models/schemas.py

```python
# backend/app/models/schemas.py

class TaskStatus(str, Enum):
    PENDING   = "pending"    # 等待执行
    RUNNING   = "running"    # 正在执行
    COMPLETED = "completed"  # 执行完成
    FAILED    = "failed"     # 执行失败
    BLOCKED   = "blocked"    # 依赖未满足，被阻塞

class Task(BaseModel):
    id: str                       # 如 "task_1", "task_2"
    description: str              # 任务描述，如"查询中国2020-2024年GDP"
    dependencies: list[str] = []  # 依赖的其他任务 ID，如 ["task_1"]
    status: TaskStatus = TaskStatus.PENDING
    result: str | None = None     # 执行结果文本
    tool_calls: list[dict] = []   # 调用了哪些工具（记录用）
```

### Task 的依赖关系示例

```
用户问题："比较中美GDP，并分析差距原因"

Planner 生成的任务：
  task_1: "查询中国2020-2024年GDP"     dependencies: []
  task_2: "查询美国2020-2024年GDP"     dependencies: []
  task_3: "对比分析中美GDP差距"         dependencies: ["task_1", "task_2"]

执行顺序：
  task_1 和 task_2 没有依赖 → 先执行 task_1
  task_1 完成 → 执行 task_2
  task_2 完成 → task_3 的依赖都满足了 → 执行 task_3
```

---

## 5. 图状态 — graph/state.py

`AgentState` 是整个 LangGraph 图的"共享内存"，所有节点通过它传递数据。

```python
class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]  # 对话消息列表
    user_input: str                           # 本轮用户原始输入
    intent: str                               # "simple_chat" 或 "complex_research"
    response_style: str                       # "brief" 或 "detailed"
    tasks: list[Task]                         # Planner 输出的任务列表
    task_results: Annotated[dict[str, str], _merge_task_results]  # 任务执行结果
    final_report: str                         # Writer 输出的最终报告
    conversation_history: str                 # 历史摘要（跨轮传入）
    thread_id: str                            # 会话 ID
    current_task: Optional[Task]              # Coordinator 当前挑选的任务
    dependencies_context: str                 # 前置任务结果（注入给 Worker）
```

### 理解 `TypedDict, total=False`

- `TypedDict`：Python 字典的类型提示方式，告诉类型检查器这个字典有哪些键
- `total=False`：所有字段都是**可选的**，允许节点只返回它修改的字段，而不是返回完整字典

例如，Taker 节点只需要返回：
```python
return {"intent": "complex_research", "response_style": "brief"}
```
而不需要把 `tasks`、`task_results` 等都带上。

### 理解 Reducer（归约器）

LangGraph 允许为状态字段指定"当节点更新这个字段时如何合并"。

**`add_messages` reducer（来自 LangGraph）**

```python
messages: Annotated[list, add_messages]
```
行为：新消息**追加**到列表末尾，而不是覆盖整个列表。
这样每个节点只需返回新增的消息，历史消息自动保留。

**自定义 `_merge_task_results` reducer**

```python
def _merge_task_results(existing, update):
    if update is None:
        return {}      # None = 跨轮重置（清空上一轮残留）
    if not existing:
        return update  # 空字典时直接用新值
    return existing | update  # 合并两个字典（同一轮内多个 Worker 累积结果）
```

为什么需要自定义？

- 问题：如果用 `operator.or_` 作为 reducer，无法区分"清空"和"合并"
- 设计：约定 `None` = 清空，`dict` = 合并
- 每轮开始时，`routes_chat.py` 传入 `task_results: None`，触发清空
- Worker 执行完成后返回 `{task.id: result_text}`，触发合并

---

## 6. 图构建 — graph/builder.py 与 edges.py

### builder.py — 把节点和边组装成图

```python
def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # 注册所有节点
    graph.add_node("taker", taker_node)
    graph.add_node("simple_chat", simple_chat_node)
    graph.add_node("planner", planner_node)
    graph.add_node("coordinator", coordinator_node)
    graph.add_node("worker", worker_node)
    graph.add_node("writer", writer_node)

    # 固定边：A → B，永远走这条路
    graph.add_edge(START, "taker")       # 入口必经 taker
    graph.add_edge("simple_chat", END)   # 简单对话直接结束
    graph.add_edge("planner", "coordinator")  # 规划完就去调度
    graph.add_edge("coordinator", "worker")   # 调度完就去执行
    graph.add_edge("writer", END)             # 写完报告就结束

    # 条件边：根据函数返回值决定走哪条路
    graph.add_conditional_edges(
        "taker",
        route_by_intent,           # 路由函数
        {
            "simple_chat": "simple_chat",
            "complex_research": "planner",
        },
    )

    graph.add_conditional_edges(
        "worker",
        check_progress,
        {
            "coordinator": "coordinator",  # 还有任务继续循环
            "writer": "writer",            # 全部完成生成报告
        },
    )

    return graph

def get_compiled_graph(checkpointer):
    return build_graph().compile(checkpointer=checkpointer)
```

**图的完整执行路径：**

```
简单问题：START → taker → simple_chat → END

研究问题：START → taker → planner → coordinator → worker
                                          ↑              │
                                          └──(more tasks)┘
                                                         │(all done)
                                                         ▼
                                                      writer → END
```

### edges.py — 条件路由函数

路由函数的作用：根据当前状态，返回一个字符串，LangGraph 用这个字符串查找下一个节点。

```python
def route_by_intent(state: AgentState) -> str:
    intent = state.get("intent", "simple_chat")
    if intent == "complex_research":
        return "complex_research"
    return "simple_chat"

def check_progress(state: AgentState) -> str:
    completed = set(state.get("task_results", {}).keys())  # 已完成的任务 ID 集合
    all_task_ids = {t.id for t in state.get("tasks", [])}  # 所有任务 ID 集合

    if all_task_ids and completed >= all_task_ids:  # 全部完成
        return "writer"
    return "coordinator"  # 还有未完成的
```

---

## 7. 节点详解 — graph/nodes/

每个节点都是一个**异步函数**，签名为 `async def xxx_node(state: AgentState, config) -> dict`。
- 接收完整的 `AgentState`
- 返回一个 `dict`，只包含本节点更新的字段
- LangGraph 负责把返回的字段合并回状态（通过 reducer）

---

### 7.1 Taker — 意图分类

**文件：** `graph/nodes/taker.py`

**职责：** 判断用户输入是"简单闲聊"还是"需要数据研究"，同时判断回答风格（简洁/详细）

```python
async def taker_node(state: AgentState, config) -> dict:
    intent, response_style = await classify_intent(
        TAKER_SYSTEM_PROMPT, state["user_input"]
    )
    emit_sse("intent_classified", {"intent": intent, "response_style": response_style})
    return {"intent": intent, "response_style": response_style}
```

**分类逻辑（来自 taker.py 提示词）：**

| 类别 | 触发条件 | 示例 |
|------|---------|------|
| `simple_chat` | 纯问候、关于系统的元问题 | "你好"、"你能做什么？" |
| `complex_research` | 任何涉及经济数据、指标、国家、年份、趋势 | "中国2024年GDP是多少？" |

规则：**遇到疑问时默认 `complex_research`**，因为进数据路径顶多多查一次，进简单路径却可能漏掉用户真正想要的数据。

**`response_style` 判断：**
- `"brief"`：用户只想要快速答案（默认值）
- `"detailed"`：用户说了"分析"、"报告"、"详细"、"explain"等词

---

### 7.2 Planner — 任务规划

**文件：** `graph/nodes/planner.py`

**职责：** 把用户的复杂研究需求拆解成带依赖关系的任务列表

```python
async def planner_node(state: AgentState, config) -> dict:
    # 构建提示词（注入历史摘要 + 今天日期 + 可用工具列表）
    prompt = PLANNER_SYSTEM_PROMPT.format(
        today=date.today().isoformat(),        # 让 LLM 知道"现在"是哪天
        conversation_history=conv_section,     # 历史摘要（防止重复查询）
        user_input=state["user_input"],
        available_tools=TOOL_DESCRIPTIONS,     # 告诉 LLM 有哪些工具可用
    )

    tasks = await plan_tasks(prompt, state["user_input"], ...)

    emit_sse("plan_generated", {"tasks": [t.model_dump() for t in tasks]})

    return {
        "tasks": tasks,
        "task_results": {},  # 初始化为空字典（但实际重置在 routes_chat.py 中用 None）
    }
```

**Planner 接收什么信息？**

- 用户原始问题
- 今天日期（防止 LLM 把"最新"理解成它的训练截止日期）
- 对话历史摘要（防止重复查上一轮已有的数据）
- 工具列表描述（LLM 知道有哪些工具才能合理规划任务）

**输出格式（结构化）：**

```json
{
  "tasks": [
    {"id": "task_1", "description": "查询中国2020-2024年GDP", "dependencies": []},
    {"id": "task_2", "description": "查询美国2020-2024年GDP", "dependencies": []},
    {"id": "task_3", "description": "对比分析差距及原因",    "dependencies": ["task_1", "task_2"]}
  ]
}
```

---

### 7.3 Coordinator — 任务调度

**文件：** `graph/nodes/coordinator.py`

**职责：** 从任务列表中挑出下一个"可以执行"的任务（依赖已满足且未完成）

```python
async def coordinator_node(state: AgentState, config) -> dict:
    completed = set(state.get("task_results", {}).keys())  # 已完成的 task_id
    tasks = state.get("tasks", [])

    for task in tasks:
        if task.id in completed:
            continue  # 已完成，跳过
        deps_met = all(dep in completed for dep in task.dependencies)
        if deps_met:
            # 找到了！构建依赖上下文（前置任务的结果拼成文字）
            deps_context = _build_deps_context(task, state.get("task_results", {}))
            return {
                "current_task": task,
                "dependencies_context": deps_context,
            }

    return {"current_task": None, "dependencies_context": ""}
```

**`_build_deps_context` 的作用：**

把前置任务的执行结果拼成一段文字，注入给 Worker。这样 Worker 在执行 `task_3`（对比分析）时，能直接看到 `task_1` 和 `task_2` 的 GDP 数据，不需要重新查询。

```
[task_1 结果]
中国GDP数据：2020年14.7万亿美元，2024年17.9万亿美元...

[task_2 结果]
美国GDP数据：2020年21.0万亿美元，2024年27.3万亿美元...
```

---

### 7.4 Worker — 任务执行

**文件：** `graph/nodes/worker.py`

这是系统最核心的节点，实现了完整的 **Agentic Loop（智能体循环）**：

```
构建消息 → 调用 LLM（绑定工具）→
  ├── LLM 返回文字（无工具调用）→ 任务完成，返回结果
  └── LLM 返回工具调用指令 →
        ├── 并发执行所有工具
        ├── 把工具结果追加到消息列表
        └── 再次调用 LLM → （循环）
```

```python
TOOLS = [world_bank_api, imf_data_api, oecd_api, eurostat_api,
         fred_api, alpha_vantage_api, brave_search, python_calculator]

async def worker_node(state: AgentState, config) -> dict:
    task = state.get("current_task")
    llm = get_tool_llm(TOOLS, temperature=0)  # 绑定了所有工具的 LLM

    messages = [SystemMessage(content=system_prompt)]  # 包含任务描述和依赖上下文

    for _ in range(settings.MAX_TOOL_ROUNDS):  # 最多循环 5 次
        response = await llm.ainvoke(messages)

        if not response.tool_calls:
            # LLM 决定不再调用工具，直接给出结论
            result_text = response.content
            emit_sse("task_status_update", {"task_id": task.id, "status": "completed"})
            return {"task_results": {task.id: result_text}}

        # LLM 要调用工具
        messages.append(response)  # 把 AI 的工具调用指令追加到消息列表

        # 并发执行所有工具（asyncio.gather）
        tool_results = await asyncio.gather(*[
            _invoke_tool(tc["name"], tc["args"])
            for tc in response.tool_calls
        ])

        # 把工具结果追加回消息列表，让 LLM 看到
        for tool_call, tool_result in zip(response.tool_calls, tool_results):
            messages.append(ToolMessage(
                content=tool_result[:3000],  # 截断，防止超出 context 窗口
                tool_call_id=tool_call["id"],
            ))
        # 循环，再次调用 LLM
```

**并发工具调用：**

```python
# LLM 可能一次请求调用多个工具，例如同时查多个国家
tool_results = await asyncio.gather(*[
    _invoke_tool(tc["name"], tc["args"])
    for tc in response.tool_calls
])
```

`asyncio.gather` 让多个工具调用**并发执行**，而不是串行等待，节省时间。

**工具调用超时保护：**

```python
result = await asyncio.wait_for(
    tool_fn.ainvoke(tool_args),
    timeout=settings.TOOL_CALL_TIMEOUT,  # 默认 30 秒
)
```

防止某个外部 API 挂起导致整个系统卡死。

---

### 7.5 Writer — 报告汇总

**文件：** `graph/nodes/writer.py`

**职责：** 把所有任务的执行结果汇总，根据 `response_style` 生成简洁回答或完整报告

```python
async def writer_node(state: AgentState, config) -> dict:
    llm = get_streaming_llm(temperature=0.3)  # streaming=True，逐 token 输出

    response_style = state.get("response_style", "brief")
    # 根据风格构建不同的格式指令
    style_instruction = (
        "Output format: BRIEF. 直接给数据和 1-2 句解释，不要长篇大论..."
        if response_style == "brief"
        else
        "Output format: DETAILED. 完整 Markdown 报告，含##章节、表格、分析..."
    )

    report = ""
    async for chunk in llm.astream([SystemMessage(content=prompt)]):
        if chunk.content:
            report += chunk.content
            emit_sse("report_token", {"token": chunk.content})  # 逐 token 推送给前端

    emit_sse("done", {})  # 告诉前端流式输出结束

    return {
        "final_report": report,
        "messages": [AIMessage(content=report)],  # 追加到消息历史
    }
```

**`temperature=0.3`** — 写作任务用稍高温度（0.3）使输出流畅自然，而分类/规划任务用 `temperature=0`（完全确定性）。

---

### 7.6 SimpleChat — 简单对话

**文件：** `graph/nodes/simple_chat.py`

处理问候、元问题等不需要数据工具的对话。直接流式输出，逻辑简单。

```python
async def simple_chat_node(state: AgentState, config) -> dict:
    llm = get_streaming_llm(temperature=0.7)  # 闲聊用更高温度，更自然

    full_response = ""
    async for chunk in llm.astream([
        SystemMessage(content=SIMPLE_CHAT_PROMPT + style_note),
        *state.get("messages", []),  # 传入完整对话历史，支持多轮
    ]):
        if chunk.content:
            full_response += chunk.content
            emit_sse("chat_token", {"token": chunk.content})

    emit_sse("done", {})
    return {"messages": [AIMessage(content=full_response)]}
```

---

## 8. LLM 层 — llm/

### 8.1 client.py — LLM 工厂

不同场景需要不同配置的 LLM，`client.py` 提供四种工厂函数：

```python
def get_chat_llm(*, temperature=0, streaming=False) -> ChatOpenAI:
    """基础 LLM 客户端。"""
    return ChatOpenAI(model=settings.MODEL_NAME, temperature=temperature,
                      streaming=streaming, timeout=settings.LLM_CALL_TIMEOUT)

def get_streaming_llm(*, temperature=0) -> ChatOpenAI:
    """流式 LLM，逐 token 输出。Writer 和 SimpleChat 使用。"""
    return get_chat_llm(temperature=temperature, streaming=True)

def get_tool_llm(tools, *, temperature=0) -> RunnableBinding:
    """绑定工具的 LLM。Worker 使用，LLM 可以调用工具。"""
    return get_chat_llm(temperature=temperature).bind_tools(list(tools))

def get_structured_llm(output_model, *, temperature=0) -> RunnableBinding:
    """结构化输出 LLM。Taker 和 Planner 使用，保证输出符合 Pydantic 模型。"""
    return get_chat_llm(temperature=temperature).with_structured_output(output_model)
```

| 函数 | 使用场景 | 关键特性 |
|------|---------|---------|
| `get_streaming_llm` | Writer、SimpleChat | `streaming=True`，支持 `astream()` |
| `get_tool_llm` | Worker | `.bind_tools()`，LLM 可以发出工具调用指令 |
| `get_structured_llm` | Taker、Planner | `.with_structured_output()`，强制 JSON 格式 |

### 8.2 output_models.py — 结构化输出模型

```python
class IntentOutput(BaseModel):
    intent: Literal["simple_chat", "complex_research"] = "simple_chat"
    response_style: Literal["brief", "detailed"] = "brief"

class PlannedTaskOutput(BaseModel):
    id: str
    description: str
    dependencies: list[str] = Field(default_factory=list)

class TaskPlanOutput(BaseModel):
    tasks: list[PlannedTaskOutput] = Field(default_factory=list)
```

这些模型配合 `get_structured_llm()` 使用。OpenAI 的 structured output 功能（Function Calling + JSON mode）保证 LLM 输出**严格符合 Pydantic 模型定义**，不会有格式错误。

### 8.3 wrapper.py — 高层调用封装

封装了两个常用的 LLM 调用场景，并内置了**降级（fallback）逻辑**：

```python
async def classify_intent(system_prompt, user_input) -> tuple[str, str]:
    """调用结构化 LLM 分类意图。失败时降级到 ('simple_chat', 'brief')。"""
    try:
        llm = get_structured_llm(IntentOutput, temperature=0)
        result = await llm.ainvoke([SystemMessage(...), HumanMessage(...)])
        return result.intent, result.response_style
    except Exception:
        return "simple_chat", "brief"  # 降级，不崩溃

async def plan_tasks(system_prompt, user_input, *, fallback_description) -> list[Task]:
    """调用结构化 LLM 规划任务。失败时降级到单任务。"""
    try:
        llm = get_structured_llm(TaskPlanOutput, temperature=0)
        result = await llm.ainvoke(...)
        tasks = build_tasks_from_plan(result)
        if tasks:
            return tasks
    except Exception:
        pass
    return [Task(id="task_1", description=fallback_description, ...)]  # 降级
```

**为什么要降级？** 结构化输出偶尔会因为 API 异常失败，降级保证系统始终能给用户一个结果，而不是崩溃。

---

## 9. SSE 流式推送 — streaming/sse.py

SSE（Server-Sent Events）是一种让服务器主动向客户端推送数据的技术，用于实现"打字机效果"和实时进度显示。

```python
# streaming/sse.py

from langgraph.config import get_stream_writer

def emit_sse(event_type: str, data: dict) -> None:
    try:
        write = get_stream_writer()    # 获取当前图执行上下文的写入器
        write({"event": event_type, "data": data})
    except Exception:
        pass  # 非流式上下文（如单元测试）中静默忽略
```

### 工作原理全链路

```
① 节点内部调用:
   emit_sse("report_token", {"token": "中国GDP..."})

② LangGraph get_stream_writer() 把数据写入流缓冲区

③ API 层接收（routes_chat.py）:
   async for chunk in graph.astream(input_state, config, stream_mode="custom"):
       event_type = chunk["event"]   # "report_token"
       data = chunk["data"]          # {"token": "中国GDP..."}
       yield {"event": event_type, "data": json.dumps(data)}

④ EventSourceResponse 格式化为 SSE 协议发送给浏览器:
   event: report_token
   data: {"token": "中国GDP..."}

⑤ 前端 JavaScript 接收:
   if (eventType === 'report_token') {
       assistantContent += payload.token
       // 更新 UI 显示新的 token
   }
```

### 所有 SSE 事件类型

| 事件名 | 触发节点 | payload 内容 | 前端用途 |
|--------|---------|------------|---------|
| `intent_classified` | Taker | `{intent, response_style}` | 知道走哪条路径 |
| `plan_generated` | Planner | `{tasks: [...]}` | 在右侧面板显示任务列表 |
| `task_status_update` | Worker | `{task_id, status}` | 更新任务状态指示灯 |
| `tool_call_start` | Worker | `{task_id, tool_name, tool_input}` | 显示正在调用哪个工具 |
| `tool_call_result` | Worker | `{task_id, tool_name, tool_output}` | 标记工具调用完成 |
| `worker_token` | Worker | `{task_id, token}` | （目前前端未单独显示）|
| `report_token` | Writer | `{token}` | 打字机效果渲染报告 |
| `chat_token` | SimpleChat | `{token}` | 打字机效果渲染对话 |
| `done` | Writer/SimpleChat | `{}` | 标记流结束 |
| `error` | API 层 | `{message}` | 显示错误提示 |

---

## 10. 外部工具 — tools/

所有工具都用 LangChain 的 `@tool` 装饰器定义，自动生成工具描述供 LLM 选择调用。

### 工具一览

| 工具 | 数据来源 | 数据特点 | 需要 API Key |
|------|---------|---------|------------|
| `world_bank_api` | 世界银行 | GDP、通胀、失业率等宏观指标，150+ 国家，滞后1-2年 | 否 |
| `imf_data_api` | IMF | 经常账户、债务、储备等国际金融指标 | 否 |
| `oecd_api` | OECD | 发达国家详细经济统计 | 否 |
| `eurostat_api` | 欧盟统计局 | 欧洲地区专项数据 | 否 |
| `fred_api` | 美联储 FRED | 美国宏观数据，更新及时 | 是（免费申请）|
| `alpha_vantage_api` | Alpha Vantage | 实时汇率、美股、大宗商品 | 是（免费申请）|
| `brave_search` | 网页搜索 | 最新新闻、政策、市场分析 | 是（付费）|
| `python_calculator` | 本地计算 | 数学运算、增长率计算 | 否 |

### 典型工具实现：world_bank_api

```python
@tool
async def world_bank_api(
    country_code: str,    # 如 "CHN", "USA"
    indicator: str,       # 如 "NY.GDP.MKTP.CD"（GDP，现价美元）
    start_year: int = 2018,
    end_year: int | None = None,
) -> str:
    if end_year is None:
        end_year = date.today().year  # 默认查到今年，不用手动维护

    url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/{indicator}?..."

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    # 解析并返回 JSON 格式数据
    records = [{"year": item["date"], "value": item["value"]} for item in data[1] ...]
    return json.dumps(records)
```

**为什么用 `httpx` 而不是 `requests`？**
`requests` 是同步库，在异步 FastAPI 中使用会阻塞事件循环。`httpx` 支持 `async with`，完全异步，不会阻塞。

### 工具的数据新鲜度策略

```
实时数据（当天）  → alpha_vantage（汇率、股票）
                  → brave_search（新闻、最新政策）

近期数据（月/季）  → fred_api（美国宏观经济指标）

年度数据（1-2年滞后）→ world_bank_api、imf、oecd、eurostat
```

Worker 的 prompt 中有规则：当统计数据库找不到最近数据时，**必须用 brave_search 补充**。

---

## 11. 数据库层 — db/

项目使用 PostgreSQL，有两套连接系统并存：

| 系统 | 库 | 用途 |
|------|-----|------|
| asyncpg | `asyncpg` | 业务表（users, threads, messages）的读写 |
| LangGraph Checkpointer | `psycopg3` | 图状态快照（checkpointer 内部管理）|

两者连接**同一个 PostgreSQL 数据库**，只是用了不同的驱动和表。

### 11.1 connection.py — 连接池与建表

```python
# 数据库表结构

users 表:
  id            TEXT PRIMARY KEY     # UUID
  email         TEXT UNIQUE          # 登录邮箱
  password_hash TEXT                 # bcrypt 哈希，不存明文
  created_at    TIMESTAMPTZ

threads 表（= 一个对话会话）:
  id              TEXT PRIMARY KEY   # 与 LangGraph thread_id 相同
  user_id         TEXT → users(id)
  title           TEXT               # 自动取第一条消息前 60 字
  summary         TEXT               # 历史摘要（定长压缩）
  summary_up_to   INT                # 生成摘要时已有多少条消息
  message_count   INT
  created_at      TIMESTAMPTZ
  updated_at      TIMESTAMPTZ

messages 表:
  id        TEXT PRIMARY KEY
  thread_id TEXT → threads(id) ON DELETE CASCADE  # 删线程时消息也自动删
  role      TEXT  CHECK (role IN ('user', 'assistant'))
  content   TEXT
  created_at TIMESTAMPTZ
```

**连接池参数：**
```python
pool = await asyncpg.create_pool(
    dsn=dsn,
    min_size=2,   # 始终保持 2 个空闲连接
    max_size=10,  # 最多同时 10 个连接
    command_timeout=60,
)
```

**为什么用连接池？**
数据库连接建立需要时间（TCP 握手 + 认证），池化让连接可以**复用**。每次请求从池中借一个连接，用完归还，而不是每次重新建连。

### 11.2 repositories/thread.py

Repository 模式：把 SQL 查询封装成语义化的 Python 函数，调用者不需要写 SQL。

```python
# 关键函数说明

get_or_create_thread(thread_id, user_id, pool)
# 幂等写入：线程不存在则创建，已存在则直接返回
# 使用 ON CONFLICT DO NOTHING，防止并发重复插入报错

set_title_if_empty(thread_id, title, pool)
# 只在 title IS NULL 时更新，实现"首条消息自动命名"
# 防止后续消息覆盖已有标题

increment_message_count(thread_id, pool)
# UPDATE ... SET message_count = message_count + 1
# 原子操作，防止并发计数错误

update_summary(thread_id, summary, summary_up_to, pool)
# 保存 LLM 生成的摘要 + 记录生成时的消息数量
# summary_up_to 用于计算"距上次摘要新增了多少条"

delete_thread(thread_id, pool)
# DELETE FROM threads WHERE id = $1
# CASCADE 会自动删除对应的所有 messages

list_threads_for_user(user_id, pool, limit=50)
# 按 updated_at DESC 排序，最新对话排前面
```

### 11.3 repositories/message.py

```python
save_message(thread_id, role, content, pool)
# INSERT INTO messages，自动生成 UUID 作为 ID

get_messages(thread_id, pool)
# SELECT ... ORDER BY created_at ASC
# 按时间顺序返回，供前端展示历史
```

### 11.4 repositories/user.py

```python
create_user(email, password_hash, pool)
# INSERT INTO users（包含 email 和哈希密码）
# 返回 None 如果邮箱已被注册（UNIQUE 约束冲突）

get_user_by_email(email, pool)
# 登录时用，通过邮箱找用户，验证密码

get_user_by_id(user_id, pool)
# JWT 解码后验证用户存在
```

---

## 12. 服务层 — services/

### 12.1 auth.py — JWT 认证

整个认证流程：

```
注册：用户提交 email + password
  → hash_password(password)  生成 bcrypt 哈希
  → 存入 users 表
  → create_access_token(user_id)  生成 JWT
  → 返回 JWT 给前端

登录：用户提交 email + password
  → 从 DB 查到用户
  → verify_password(plain, hashed)  验证密码
  → create_access_token(user_id)  生成 JWT
  → 返回 JWT 给前端

后续请求：前端在 Header 带上 Authorization: Bearer <token>
  → get_current_user_id(credentials=Depends(_bearer))
  → 解码 JWT，验证签名和过期时间
  → 返回 user_id 给路由函数
```

**JWT 结构：**
```
header.payload.signature

payload = {
    "sub": "user-uuid-xxx",  # subject = user_id
    "exp": 1234567890        # 过期时间戳（72小时后）
}
```

**`bcrypt` 密码哈希：**
- 单向加密，无法反推原始密码
- 内置 salt（随机盐），同一密码每次哈希结果不同，防止彩虹表攻击
- 验证时：`bcrypt.verify(plain, stored_hash)` 内部重新计算并比较

**FastAPI 依赖注入：**
```python
# 在路由函数中这样使用
@router.post("/api/chat")
async def chat(
    body: ChatRequest,
    user_id: str = Depends(get_current_user_id),  # 自动提取并验证 JWT
):
    # user_id 已经是验证过的真实用户 ID
```

如果 token 无效或过期，`get_current_user_id` 自动抛出 `401 Unauthorized`，路由函数不会被调用。

### 12.2 checkpointer.py — 图状态持久化

```python
def get_checkpointer_context():
    dsn = settings.DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")
    return AsyncPostgresSaver.from_conn_string(dsn)
```

**LangGraph Checkpointer 做什么？**

每次图执行完一个节点，checkpointer 自动把当前 `AgentState` 快照保存到 PostgreSQL。下次同一个 `thread_id` 发起请求时，自动恢复上一轮的状态，实现多轮对话记忆。

```
第1轮：用户问"分析中国GDP"
  → 图执行 → AgentState 快照保存到 DB（thread_id="abc"）

第2轮：用户问"再加上失业率"（同一 thread_id）
  → LangGraph 从 DB 恢复第1轮的 messages
  → Taker/Planner 能看到上一轮的对话内容
  → 只新查失业率，不重复查 GDP
```

**为什么用 `async with`？**

`AsyncPostgresSaver.from_conn_string()` 返回的是一个**异步上下文管理器**，内部持有一个持久的 psycopg3 连接。必须在整个 app 生命周期内保持这个连接打开，`async with` 保证进入时初始化、退出时清理。

### 12.3 summarization.py — 对话摘要压缩

**问题：** 对话历史越来越长，会超出 LLM 的 context 窗口（且费用越来越高）

**解决方案：** 当消息积累到阈值（默认 10 条）时，用 LLM 把全部历史压缩成一个≤400字的摘要。

```python
async def summarize_if_needed(thread_id, pool):
    thread = await get_thread(thread_id, pool)

    # 计算"距上次摘要新增了多少条消息"
    new_since_summary = thread["message_count"] - thread["summary_up_to"]
    if new_since_summary < settings.SUMMARIZE_THRESHOLD:
        return  # 还没到阈值，不触发

    # 获取全部消息，生成新摘要
    messages = await get_messages(thread_id, pool)
    new_summary = await _generate_summary(thread["summary"] or "", messages)
    await update_summary(thread_id, new_summary, thread["message_count"], pool)
```

**摘要提示词策略：**

```
现有摘要（来自更早的对话，如果有的话）：
  "用户探讨了中国2020-2023年GDP趋势，发现年均增速4.2%..."

需要整合的新消息：
  [USER]: 那美国的失业率呢？
  [ASSISTANT]: 美国2020-2023失业率从8.1%降至3.7%...

→ LLM 生成新摘要（合并两者）：
  "用户探讨了中美经济对比：中国GDP年均增速4.2%；美国失业率
   从2020年8.1%降至2023年3.7%..."
```

**下一轮对话时，`conversation_history` 注入的是这个压缩摘要**，而不是原始消息列表，所以 context 长度恒定。

### 12.4 memory.py — 历史提取

从 LangGraph checkpointer 中提取历史消息的工具函数（辅助性质，主要摘要流程在 summarization.py）：

```python
async def build_conversation_history(graph, thread_id: str) -> str:
    state = await graph.aget_state({"configurable": {"thread_id": thread_id}})
    messages = state.values.get("messages", [])

    lines = []
    for msg in messages:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        if isinstance(msg.content, str) and msg.content.strip():
            lines.append(f"[{role}]: {msg.content}")

    return "\n".join(lines)
```

---

## 13. API 路由 — api/

### 13.1 routes_auth.py

```
POST /api/auth/register  → 注册新用户
POST /api/auth/login     → 登录，返回 JWT
GET  /api/auth/me        → 获取当前用户信息（需要 token）
```

注册流程：
1. 验证密码≥6字符
2. `hash_password(body.password)` 生成 bcrypt 哈希
3. 调用 `user_repo.create_user()`，若邮箱重复返回 `None`
4. 生成 JWT token，返回给前端

登录流程：
1. 通过邮箱查找用户
2. `verify_password(body.password, user["password_hash"])` 验证
3. 成功则生成新 JWT 返回

### 13.2 routes_chat.py（核心路由）

这是最复杂的路由，整合了所有服务：

```python
@router.post("/api/chat")
async def chat(request, body: ChatRequest, user_id = Depends(get_current_user_id)):

    thread_id = body.thread_id or str(uuid4())  # 新会话自动生成 UUID

    # 1. 确保 DB 中存在 user + thread 记录
    await thread_repo.get_or_create_thread(thread_id, user_id, pool)

    # 2. 首条消息自动成为标题
    await thread_repo.set_title_if_empty(thread_id, body.message, pool)

    # 3. 从 DB 加载历史摘要（定长，不随轮次膨胀）
    conversation_history = await get_context_for_thread(thread_id, pool)

    async def event_generator():
        input_state = {
            "user_input": body.message,
            "conversation_history": conversation_history,
            # ── 跨轮任务状态隔离 ──────────────────────────────
            "tasks": [],
            "task_results": None,  # None → 触发 reducer 清空上轮残留
            "current_task": None,
            # ...
        }

        assistant_tokens = []  # 收集 token 用于流结束后持久化

        # 4. 运行 LangGraph 图，以 SSE 流式返回
        async for chunk in graph.astream(input_state, config, stream_mode="custom"):
            event_type = chunk["event"]
            data = chunk["data"]

            # 收集 assistant 的输出
            if event_type in ("report_token", "chat_token"):
                assistant_tokens.append(data.get("token", ""))

            yield {"event": event_type, "data": json.dumps(data)}

        # 5. 流结束后：持久化消息到 DB
        await message_repo.save_message(thread_id, "user", body.message, pool)
        await message_repo.save_message(thread_id, "assistant", "".join(assistant_tokens), pool)
        await thread_repo.increment_message_count(thread_id, pool)

        # 6. 触发摘要压缩（如果消息数超过阈值）
        await summarize_if_needed(thread_id, pool)

    return EventSourceResponse(
        event_generator(),
        headers={"X-Thread-Id": thread_id, "X-User-Id": user_id},
    )
```

**关键设计：先流式返回，流结束后持久化**

消息不在流开始时保存，而是等流结束、assistant 输出完整后再保存。原因：流式过程中 token 是碎片，只有收齐才能存完整的 assistant 消息。

### 13.3 routes_history.py

```
GET /api/history/{thread_id}
```

从业务 `messages` 表读取历史，返回给前端展示。与 LangGraph checkpointer 无关（两套独立存储）。

### 13.4 routes_threads.py

```
GET    /api/threads          → 列出用户所有对话线程（按最近更新排序）
DELETE /api/threads/{id}     → 删除线程及其所有消息（CASCADE）
```

---

## 14. 完整数据流追踪

以用户问"中美2024年GDP对比"为例，追踪整个系统：

```
① 前端发送:
   POST /api/chat
   Authorization: Bearer eyJhbGciOiJIUzI1...
   {"message": "中美2024年GDP对比", "thread_id": null}

② routes_chat.py:
   - JWT 验证 → user_id = "user-abc"
   - 生成 thread_id = "uuid-xyz"（新会话）
   - DB: 创建 users + threads 记录
   - DB: 设置 title = "中美2024年GDP对比"
   - DB: 加载历史摘要（空，第一轮）
   - 组装 input_state
   - graph.astream(input_state, stream_mode="custom")

③ Taker 节点:
   - classify_intent() → ("complex_research", "brief")
   - emit_sse("intent_classified", {...})
   → SSE: event: intent_classified / data: {"intent": "complex_research", ...}

④ Planner 节点:
   - plan_tasks() → [task_1: 查中国GDP, task_2: 查美国GDP, task_3: 对比分析]
   - emit_sse("plan_generated", {"tasks": [...]})
   → SSE: event: plan_generated / data: {"tasks": [...]}

⑤ Coordinator 节点:
   - 找到 task_1（无依赖，第一个）
   - return {current_task: task_1, dependencies_context: ""}

⑥ Worker 节点（执行 task_1）:
   - emit_sse("task_status_update", {"task_id": "task_1", "status": "running"})
   → SSE: event: task_status_update
   
   - LLM 决定调用 world_bank_api(country_code="CHN", indicator="NY.GDP.MKTP.CD", ...)
   - emit_sse("tool_call_start", {"task_id": "task_1", "tool_name": "world_bank_api", ...})
   → SSE: event: tool_call_start
   
   - 调用 world_bank_api → 返回中国GDP数据
   - emit_sse("tool_call_result", {...})
   → SSE: event: tool_call_result
   
   - LLM 再次调用（无更多工具需求），输出文字总结
   - emit_sse("task_status_update", {"status": "completed"})
   - return {"task_results": {"task_1": "中国GDP: 2024年约17.9万亿美元..."}}

⑦ check_progress: task_2 和 task_3 未完成 → coordinator

⑧ Coordinator → Worker（task_2: 查美国GDP）
   → 类似流程，查 world_bank_api(country_code="USA", ...)
   → task_results = {"task_1": "...", "task_2": "美国GDP: 27.3万亿..."}

⑨ check_progress: task_3 未完成 → coordinator

⑩ Coordinator → Worker（task_3: 对比分析）
   - dependencies_context 包含 task_1 和 task_2 的结果
   - LLM 直接用已有数据分析，可能调用 python_calculator 计算差值
   - return {"task_results": {..., "task_3": "中美GDP差距9.4万亿..."}}

⑪ check_progress: 全部完成 → writer

⑫ Writer 节点:
   - response_style = "brief" → 简洁格式指令
   - 汇总 task_1 + task_2 + task_3 的结果
   - 流式生成报告，逐 token 推送
   → SSE: event: report_token / data: {"token": "2024年"}
   → SSE: event: report_token / data: {"token": "中国GDP"}
   → SSE: event: report_token / data: {"token": "约17.9"}
   → ... （数百个 token）
   → SSE: event: done / data: {}

⑬ routes_chat.py 流结束后:
   - DB: save_message(user: "中美2024年GDP对比")
   - DB: save_message(assistant: "2024年中国GDP约17.9万亿...")
   - DB: increment_message_count × 2
   - summarize_if_needed（消息数未到阈值，跳过）

⑭ 前端收到 X-Thread-Id: "uuid-xyz"，保存供下次请求续轮
```

---

## 15. 关键设计决策解释

### 为什么不用并行 Worker？

最初设计考虑过用 LangGraph 的 `Send API` 同时并行执行多个 Worker，但改为顺序执行。原因：

- 并行执行时，多个 Worker 同时写 `task_results`，reducer 竞争导致状态追踪 Bug
- 顺序执行更简单可靠，Coordinator 每次只挑一个任务
- 实践中，任务之间往往有依赖（后一个任务需要前一个的结果），并行收益有限

### 为什么有两套数据库连接？

- **asyncpg**（业务层）：更快、轻量，接口简洁，适合高频的业务 CRUD
- **psycopg3**（checkpointer）：LangGraph 官方 checkpointer 库要求用 psycopg3，无法改变

两者都连接同一个 PostgreSQL，各管各的表，互不干扰。

### 跨轮任务隔离

**问题：** 轮次1问了"中国GDP"，LangGraph checkpointer 保存了状态，包括 `task_results = {"task_1": "..."}`。轮次2问"美国失业率"时，旧的 `task_results` 还在，Coordinator 会错误地认为"task_1 已完成"。

**解决：** 每轮在 `input_state` 中显式传入 `task_results: None`。自定义 reducer `_merge_task_results` 看到 `None` 就清空，确保每轮都是干净的起点。

### 对话摘要压缩

LangGraph checkpointer 会保存全部 messages（每轮追加），长对话会无限增长，导致：
- 超出 LLM context 窗口（GPT-4o 是 128k tokens）
- 每轮费用增加

解决方案：独立维护一个压缩摘要（存在 `threads.summary`），注入给节点的是摘要而非原始消息，保证上下文长度恒定。

---

## 16. 快速启动

### 前提条件

- Python 3.11+
- Docker（运行 PostgreSQL）
- OpenAI API Key（必需）
- 其他 API Key（可选，不填时对应工具跳过）

### 步骤

```bash
# 1. 启动 PostgreSQL（在项目根目录）
docker compose up -d

# 2. 创建 Python 虚拟环境（在项目根目录）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
cd backend
pip install -r requirements.txt
pip install "bcrypt==3.2.2"  # 需要固定版本，避免与 passlib 不兼容

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env，至少填入：
#   OPENAI_API_KEY=sk-xxx
#   DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/econagent

# 5. 启动后端
cd backend
uvicorn app.main:app --reload --port 8000

# 6. 启动前端（另开终端）
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

### 环境变量说明

```env
# 必填
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/econagent

# 推荐填写（提升数据质量）
BRAVE_API_KEY=...          # 网页搜索，获取最新数据
FRED_API_KEY=...           # 美联储经济数据（免费申请）
ALPHA_VANTAGE_API_KEY=...  # 实时金融数据（免费申请）

# 安全相关（生产环境必须修改）
JWT_SECRET=your-random-secret-key-here

# 可调整的参数
MAX_TOOL_ROUNDS=5         # Worker 最多调用工具几轮
SUMMARIZE_THRESHOLD=10    # 多少条消息后触发摘要压缩
MODEL_NAME=gpt-4o         # 使用哪个 OpenAI 模型
```
