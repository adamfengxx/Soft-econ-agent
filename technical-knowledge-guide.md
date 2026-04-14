# EconAgent 技术知识点学习手册

> 这份文档不是“架构说明书”，而是“学习手册”。
> 它会把 `architecture.md` 里出现的技术概念、你项目当前代码里的实际实现、以及这些技术为什么存在，统一用更适合初学者理解的方式讲清楚。

---

## 1. 怎么看这份文档

如果你现在对后端、LLM、前端、数据库这些词都还比较陌生，建议按下面顺序读：

1. 先看“系统整体怎么跑起来”
2. 再看“HTTP / API / 路由 / 请求响应”
3. 再看“LangGraph 图执行”
4. 再看“LLM 调用、Pydantic 结构化输出、工具调用”
5. 最后看“数据库、认证、SSE 实时推送、前端”

你可以把这个项目理解成一个“会做研究的聊天系统”：

- 前端负责显示聊天界面
- 后端负责接请求、跑图、调模型、查数据库
- 数据库负责保存用户、线程、消息、摘要
- LangGraph 负责把复杂问题拆成多个 AI 节点来执行
- OpenAI 模型负责分类、规划、执行、总结

---

## 2. 整个项目在做什么

### 2.1 一个问题是怎么从前端走到后端的

用户在前端输入一句话，比如：

`Compare China and US GDP growth from 2020 to 2024`

流程大致是：

1. 前端把这句话通过 HTTP 请求发给后端 `/api/chat`
2. 后端先识别这是“闲聊”还是“研究任务”
3. 如果是研究任务，Planner 会把它拆成多个子任务
4. Coordinator 会挑选下一个可执行任务
5. Worker 会调用真实工具，比如 World Bank / IMF / FRED
6. Writer 会把所有结果整合成最终回答
7. 过程中后端通过 SSE 把中间进度实时推回前端
8. 最终结果落库，线程历史和摘要被更新

### 2.2 你这个项目为什么不是“普通聊天机器人”

普通聊天机器人通常是：

- 用户说一句
- 模型直接回答一句

你的项目更像“AI 研究系统”：

- 不只是回答
- 会拆任务
- 会查真实数据
- 会跨轮保留对话上下文
- 会流式展示任务状态和最终报告

这就是为什么你项目里会同时出现：

- FastAPI
- LangGraph
- OpenAI
- asyncpg / PostgreSQL
- JWT
- SSE
- React

---

## 3. HTTP、API、路由、请求响应到底是什么

### 3.1 HTTP 是什么

HTTP 是浏览器和服务器之间通信的协议。

最常见的理解方式：

- 浏览器发请求
- 服务器回响应

例如：

- `GET /api/threads`：获取线程列表
- `POST /api/chat`：发一条聊天消息
- `POST /api/auth/login`：登录

### 3.2 API 是什么

API 可以理解成“程序暴露出来给别人调用的接口”。

在你的项目里，后端暴露的 API 包括：

- `/api/auth/register`
- `/api/auth/login`
- `/api/auth/me`
- `/api/chat`
- `/api/history/{thread_id}`
- `/api/threads`

也就是说，前端不是直接碰数据库，而是通过这些 API 和后端交互。

### 3.3 Route / 路由是什么

路由就是：

“某个 URL + 某种 HTTP 方法，应该由哪段代码处理”

例如在 FastAPI 里：

```python
@router.post("/api/chat")
async def chat(...):
    ...
```

意思是：

- 当收到 `POST /api/chat`
- 就执行 `chat()` 这段函数

### 3.4 HTTP 路由层是什么

“路由层”就是离外部请求最近的一层。

它负责：

- 接收请求参数
- 做基础校验
- 从认证信息里拿当前用户
- 调用 service / repository / graph
- 把结果返回给前端

你项目里这一层主要在：

- `backend/app/api/routes_auth.py`
- `backend/app/api/routes_chat.py`
- `backend/app/api/routes_history.py`
- `backend/app/api/routes_threads.py`

### 3.5 Request 和 Response 是什么

请求 Request：

- 前端发给后端的内容
- 比如 message、thread_id、token

响应 Response：

- 后端回给前端的内容
- 比如 JSON、SSE 流、错误码

在 FastAPI 里，`Request` 对象还能拿到应用级共享资源：

- `request.app.state.graph`
- `request.app.state.db_pool`

这也是你项目为什么能在路由层里直接拿图和数据库连接池。

---

## 4. FastAPI 是什么，为什么适合你这个项目

FastAPI 是一个 Python Web 框架，特别适合：

- 写 API
- 写异步接口
- 和 Pydantic 配合做数据校验
- 生成清晰的后端结构

你的项目用它的原因很合理，因为你有：

- 普通 JSON 接口
- SSE 流式接口
- 异步数据库访问
- 异步调用外部 API
- 认证与依赖注入

### 4.1 FastAPI 的关键能力

#### 自动参数解析

比如：

```python
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
```

FastAPI 会自动把前端发来的 JSON 解析成这个对象。

#### 依赖注入

比如当前登录用户：

```python
user_id: str = Depends(get_current_user_id)
```

意思是：

- 这个参数不是前端直接传的
- 而是由另一段逻辑算出来的

#### 生命周期管理

在 `main.py` 里通过 `lifespan`：

- 启动时连数据库
- 启动时初始化 LangGraph
- 关闭时释放资源

---

## 5. 配置系统、`.env`、环境变量是什么

### 5.1 为什么要有配置系统

不同环境里，很多值都不一样：

- 本地数据库地址
- 生产数据库地址
- OpenAI API Key
- JWT Secret
- 模型名
- 超时参数

这些不适合写死在代码里，所以要放进配置。

### 5.2 `.env` 是什么

`.env` 是一个文本文件，用来写环境变量。

例如：

```env
OPENAI_API_KEY=...
DATABASE_URL=...
MODEL_NAME=gpt-4o
```

### 5.3 `BaseSettings` 是什么

你项目里用了 `pydantic-settings` 的 `BaseSettings`。

作用是：

- 从环境变量读取配置
- 自动做类型转换
- 支持默认值

比如：

```python
MAX_TOOL_ROUNDS: int = 5
```

即使 `.env` 里读出来是字符串，最终也会变成整数。

### 5.4 `load_dotenv()` 为什么存在

有些第三方库不读你的 `Settings` 对象，它们只看系统环境变量。

所以你在 `config.py` 里先把 `.env` 加载进 `os.environ`，再让 `BaseSettings` 读取，这是一个很常见的兼容做法。

---

## 6. Pydantic 是什么，为什么你项目里很多地方都在用

Pydantic 是 Python 里非常重要的数据建模和校验工具。

它最大的作用是：

- 让“数据长什么样”变清楚
- 自动校验输入是否合法
- 自动把数据转换成 Python 对象

### 6.1 在 API 输入里用 Pydantic

比如：

```python
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
```

这表示：

- `email` 必须是 email 格式
- `password` 必须存在

### 6.2 在业务模型里用 Pydantic

比如你的 `Task`：

- `id`
- `description`
- `dependencies`
- `status`

这让 Planner 和 Worker 之间传递任务时有稳定的数据结构。

### 6.3 在 LLM 结构化输出里用 Pydantic

这个特别重要。

传统模型调用常常让模型返回自由文本，后端再手写 JSON 解析，容易翻车。

你现在做的是：

- 先定义 `IntentOutput`
- 先定义 `TaskPlanOutput`
- 再让模型按这些结构返回

这就叫“结构化输出”。

好处是：

- 更稳定
- 更少手写字符串解析
- 类型更清晰
- 后续扩展更容易

---

## 7. 什么是“Pydantic 结构化输出”

### 7.1 普通输出

模型可能返回：

`I think this is a complex research question.`

这种输出人能看懂，但程序不好稳定处理。

### 7.2 结构化输出

你告诉模型：

- 按某个 schema 返回
- 比如一定要有 `intent`

然后得到：

```json
{"intent":"complex_research"}
```

在你的项目里，对应：

- `llm/output_models.py`
- `llm/wrapper.py`

### 7.3 为什么这比“自己 parse JSON”好

因为模型可能会：

- 多写解释
- 包一层 markdown
- 漏字段
- 拼错字段名

结构化输出会减少这些问题，尤其适合：

- 意图分类
- 任务规划
- 摘要输出
- 事实提取

---

## 8. LLM 调用封装是什么，为什么不能在每个节点里乱写

### 8.1 什么叫“LLM 调用封装”

意思是：

不要在每个节点里都自己 new 一次 `ChatOpenAI(...)`，而是集中封装。

你项目里这层就在：

- `backend/app/llm/client.py`
- `backend/app/llm/wrapper.py`
- `backend/app/llm/output_models.py`

### 8.2 `client.py` 做什么

这层像一个工厂：

- `get_chat_llm()`
- `get_streaming_llm()`
- `get_tool_llm()`
- `get_structured_llm()`

好处：

- 模型名统一
- 超时统一
- streaming 配置统一
- 后面切换模型更容易

### 8.3 `wrapper.py` 做什么

这层不是最底层 client，而是更高一级的“业务封装”。

比如：

- `classify_intent()`
- `plan_tasks()`

它把“怎么提示模型 + 怎么解析结构化输出 + 失败时怎么兜底”都包起来了。

### 8.4 为什么项目里需要这层

因为你的模型调用不止一个：

- taker 调一次
- planner 调一次
- worker 多轮调
- writer 再调一次

如果不收口：

- 改模型很痛苦
- 改 timeout 很分散
- 改 structured output 到处改

---

## 9. Prompt 是什么，Prompt 文件为什么单独放

Prompt 就是给模型的指令。

例如：

- 你是谁
- 你的任务是什么
- 输出格式必须怎样
- 不要做什么

你项目把 Prompt 放进：

- `prompts/taker.py`
- `prompts/planner.py`
- `prompts/worker.py`
- `prompts/writer.py`
- `prompts/simple_chat.py`

这是很好的结构，因为它把：

- “业务逻辑”
- “模型指令”

分开了。

这样你后面调提示词时，不用每次都翻节点代码。

---

## 10. LangGraph 是什么

LangGraph 是一个把 AI 工作流做成“图”的框架。

你可以把它理解成：

- 节点 Node：执行某件事
- 边 Edge：决定接下来去哪
- 状态 State：在节点之间流转的数据

### 10.1 为什么不用普通函数链

因为你的流程不是固定直线：

- 有意图分流
- 有复杂任务调度
- 有循环执行
- 有跨轮状态保存

普通 `function A -> B -> C` 不太适合这种结构。

### 10.2 图里的几个核心词

#### StateGraph

整个图对象。

#### Node

图中的执行单元，比如：

- taker
- planner
- coordinator
- worker
- writer

#### Edge

节点之间的连接关系。

比如：

- `taker -> simple_chat`
- `taker -> planner`

#### Conditional edge

根据状态决定走哪条边。

比如：

- 如果 `intent == simple_chat`
- 走 `simple_chat`
- 否则走 `planner`

#### START / END

图的起点和终点。

---

## 11. AgentState 是什么，为什么图里必须有状态

`AgentState` 是整个图执行过程中流转的数据容器。

在你的项目里，它大致包含：

- 用户输入
- 意图分类结果
- 任务列表
- task_results
- 当前任务
- 最终报告
- 对话历史摘要
- thread_id

### 11.1 为什么不能只靠函数参数

因为图执行有多个节点，而且节点执行顺序会变化。

如果没有统一状态：

- A 节点算出的结果 B 拿不到
- B 更新过的内容 C 不知道
- 很难做 checkpoint

### 11.2 Reducer 是什么

Reducer 的作用是：

“当同一个状态字段被多次更新时，怎么合并”

比如：

- `messages` 用 `add_messages`
- `task_results` 用自定义 reducer

这个知识点很关键，因为它直接决定了：

- 新值覆盖旧值
- 还是和旧值合并

---

## 12. Checkpointer 是什么

Checkpointer 是图状态持久化器。

简单说：

- 图执行到哪了
- 当前状态是什么
- 某个 thread_id 的历史状态是什么

这些都能被存到数据库里。

你项目里是：

- LangGraph
- PostgreSQL Checkpointer

### 12.1 为什么它重要

没有 checkpointer：

- 每次请求都是全新图
- 无法跨轮拿到之前的图状态

有了 checkpointer：

- 同一个 `thread_id` 可以关联到之前图的状态轨迹

### 12.2 它和业务数据库是什么关系

你现在其实有两套“存储”：

1. LangGraph checkpointer  
   用来存图状态

2. 你自己的业务 DB 表  
   用来存 users / threads / messages / summary

这个区分很重要。

- checkpointer 是“图引擎内部状态”
- 业务数据库是“你的产品数据”

---

## 13. Node 节点到底各自干什么

### 13.1 Taker

负责意图分类。

它的作用是把用户问题分成两类：

- `simple_chat`
- `complex_research`

为什么需要这个节点：

- 简单问题不需要走完整研究流程
- 复杂问题才需要拆任务、查工具、写报告

### 13.2 Planner

负责把大问题拆成任务。

例如用户问：

`Compare China and US GDP growth from 2020 to 2024`

Planner 可能拆成：

- 查中国 GDP
- 查美国 GDP
- 对比增长趋势

### 13.3 Coordinator

负责调度任务。

它会找：

- 哪些任务还没做
- 哪些任务依赖已经满足

然后挑一个当前可以执行的任务给 Worker。

### 13.4 Worker

负责真正执行任务。

这里不是单纯“让模型回答”，而是：

- 模型决定需要调用什么工具
- 调工具
- 把工具结果再喂回模型
- 重复多轮
- 最后产出结果

这就是所谓的 tool-calling loop。

### 13.5 Writer

负责把所有任务结果汇总成最终回答或报告。

它像一个总编辑，不负责取数据，而负责：

- 整理
- 总结
- 输出结构化文本

### 13.6 SimpleChat

处理闲聊、问候、简单问题。

这样系统不会每次都进入重型研究模式。

---

## 14. Tool Calling 是什么

### 14.1 普通 LLM 调用

模型只能靠自己的内部知识回答。

### 14.2 Tool Calling

模型可以决定调用外部工具，例如：

- World Bank API
- IMF API
- FRED
- Brave Search
- Calculator

### 14.3 为什么这很重要

因为宏观经济问题常常需要：

- 最新数据
- 真实数据库
- 精确数值

如果只靠模型记忆，容易过时或胡说。

### 14.4 Worker 里的 tool loop 是怎么工作的

简化理解：

1. 把任务描述发给模型
2. 模型返回：我要调用哪些工具
3. 后端实际执行工具
4. 工具结果以 `ToolMessage` 形式回传给模型
5. 模型继续思考，可能继续调工具
6. 直到模型不再请求工具，输出最终文字

这就是你 `worker.py` 最核心的技术点之一。

---

## 15. SSE 实时推送是什么

### 15.1 先理解普通 HTTP 返回

普通接口通常是：

- 前端等着
- 后端全做完
- 一次性返回

但你的聊天任务可能需要几秒甚至更久。

如果用户一直看不到中间进度，体验很差。

### 15.2 SSE 是什么

SSE 全称是 Server-Sent Events。

它允许：

- 服务器建立一个持续连接
- 不断往客户端推送事件

比如：

- `intent_classified`
- `plan_generated`
- `task_status_update`
- `tool_call_start`
- `report_token`
- `done`

### 15.3 为什么你项目适合 SSE

因为你的后端会产生很多阶段性事件：

- 刚完成意图分类
- 刚生成任务
- 某个任务开始执行
- 某个工具刚被调用
- 报告正在逐 token 输出

SSE 很适合这种“服务端不断通知前端”的场景。

### 15.4 你项目里的 SSE 结构

#### 节点内部

节点内部调用 `emit_sse()`

#### 图执行层

LangGraph 的 `stream_mode="custom"` 接收这些自定义事件

#### API 层

`routes_chat.py` 把事件封装成 SSE 格式返回

#### 前端

前端一边接流，一边实时更新 UI

### 15.5 SSE 和 WebSocket 的区别

SSE：

- 服务器单向推送给客户端
- 实现简单
- 很适合“进度流、文本流”

WebSocket：

- 双向实时通信
- 更灵活
- 复杂度更高

你的场景主要是“后端不断推状态给前端”，所以 SSE 已经很合适。

---

## 16. JWT Token 是什么

### 16.1 为什么登录后不能只靠前端说“我是某某用户”

如果前端直接传：

```json
{"user_id": "abc"}
```

后端就相信，那任何人都能伪造。

所以要有“后端签发的身份凭证”。

### 16.2 JWT 是什么

JWT 是一种 token 格式。

登录成功后，后端生成一个 token 给前端。

前端以后请求时带上这个 token：

```http
Authorization: Bearer <token>
```

后端验证：

- token 是不是我签的
- 有没有过期
- 里面的用户 ID 是谁

### 16.3 你项目里 JWT 的组成

在 `services/auth.py` 里大致是：

- `sub`：用户 ID
- `exp`：过期时间

然后用：

- `JWT_SECRET`
- `JWT_ALGORITHM`

来签发和验证。

### 16.4 JWT 登录流程

1. 用户注册
2. 密码哈希后存数据库
3. 用户登录
4. 后端验证密码
5. 验证成功后签发 JWT
6. 前端保存 token
7. 后续请求带 token

### 16.5 `Depends(get_current_user_id)` 是什么

这表示：

- 路由不再相信前端直接传 `user_id`
- 而是从 JWT 里解析当前用户

这是登录体系里很关键的一步。

---

## 17. 密码为什么不能明文存数据库

因为明文密码一旦数据库泄漏，用户真实密码就全部暴露了。

正确做法是：

- 用户注册时
- 把密码做哈希
- 存的是 `password_hash`

登录时：

- 再把用户输入的密码拿去验证哈希

你项目里这部分在 `services/auth.py` 里，用了 `passlib` / `bcrypt`。

---

## 18. Repository 模式是什么

### 18.1 为什么不把 SQL 直接写在路由里

如果路由里直接写 SQL：

- 很乱
- 很难复用
- 很难测试

所以会把数据库操作独立出来，形成 repository。

### 18.2 你项目里的 repository

- `db/repositories/user.py`
- `db/repositories/thread.py`
- `db/repositories/message.py`

可以把它理解成：

- user 相关数据库操作都放一起
- thread 相关操作都放一起
- message 相关操作都放一起

### 18.3 这样做的好处

- 路由更干净
- SQL 更集中
- 业务逻辑和存储逻辑分层

---

## 19. asyncpg、连接池、SQL 表、索引、外键是什么

### 19.1 asyncpg 是什么

`asyncpg` 是 Python 访问 PostgreSQL 的异步驱动。

因为你项目很多地方都是 async，所以数据库也用异步方式更自然。

### 19.2 连接池是什么

数据库连接很贵，不适合每个请求临时新建。

连接池的意思是：

- 先建立一批连接
- 请求来了从池里拿一个
- 用完放回去

这样性能更好。

### 19.3 表是什么

表就是数据库里的结构化存储单元。

你现在的核心表有：

- `users`
- `threads`
- `messages`

### 19.4 外键是什么

外键表示“这条数据必须依赖另一张表中的数据”。

比如：

- `threads.user_id` 指向 `users.id`
- `messages.thread_id` 指向 `threads.id`

这样数据库能帮助你保证数据关系不乱。

### 19.5 索引是什么

索引是为了提高查询速度。

例如：

- 按 `user_id` 查线程列表
- 按 `thread_id` 查消息列表

如果没有索引，数据多了会越来越慢。

### 19.6 `ON DELETE CASCADE` 是什么

意思是：

- 删掉一个 thread
- 这个 thread 下面的 messages 自动一起删

这样可以避免脏数据。

---

## 20. `thread_id`、`user_id`、message 之间是什么关系

### 20.1 user_id

代表“哪个用户”。

### 20.2 thread_id

代表“这个用户的哪一条会话”。

一个用户可以有很多线程。

### 20.3 message

代表线程里的单条消息。

所以关系是：

- 一个 user
  - 有很多 thread
    - 一个 thread
      - 有很多 message

---

## 21. 对话记忆、摘要压缩、长对话管理是什么

### 21.1 为什么不能把所有历史原文都塞给模型

因为：

- token 成本会越来越高
- 上下文会越来越长
- 响应会变慢

### 21.2 你的项目怎么做

当前思路是：

- `messages` 表保存完整历史
- `threads.summary` 保存压缩后的摘要
- 新一轮请求时，把摘要作为 `conversation_history` 注入

### 21.3 摘要服务的本质

这不是“聊天记忆魔法”，本质是：

- 用另一次 LLM 调用
- 把旧对话浓缩成更短的上下文

### 21.4 这种做法的优点

- 历史可以无限增长，但给模型的上下文保持相对稳定
- 后续节点只看摘要，不用看完整聊天记录

### 21.5 这种做法的局限

摘要永远是“有损压缩”。

也就是说：

- 不可能 100% 保留所有细节
- 所以摘要策略要 carefully 设计

---

## 22. Service 层是什么

Service 层是“业务逻辑层”。

它介于：

- 路由层
- 底层 repository / LLM / graph

之间。

你项目里比较明显的 service 有：

- `auth.py`
- `checkpointer.py`
- `summarization.py`
- `memory.py`

### 22.1 为什么要单独有 service

因为有些逻辑：

- 不是单纯数据库 CRUD
- 也不是单纯 HTTP 接口

比如：

- 验证 JWT
- 签发 token
- 生成摘要
- 管理 graph checkpointer

这些都适合放 service。

---

## 23. OpenAI / ChatOpenAI 在你项目中扮演什么角色

你的项目里，OpenAI 模型不是只负责“最后回答”。

它实际上参与了多个环节：

- Taker：意图分类
- Planner：任务拆解
- Worker：决定要不要调工具、怎么整合工具结果
- Writer：写最终报告
- Summarization：压缩历史

这说明模型在你项目里是一个“通用推理引擎”，而不是单功能聊天器。

---

## 24. 异步 `async/await` 是什么，为什么你项目大量使用

### 24.1 同步和异步的直觉区别

同步：

- 一件事没做完，就卡在那等

异步：

- 遇到等待网络、数据库、I/O 的地方，可以先让出执行权

### 24.2 你的项目为什么适合 async

因为你有很多等待型操作：

- 调 OpenAI
- 调外部经济数据 API
- 查数据库
- SSE 流式返回

如果不用 async，吞吐和响应体验都会差很多。

### 24.3 `asyncio.wait_for()` 是什么

它的作用是给某个异步操作设超时。

比如：

- 工具调用 30 秒还没回来
- 就不要一直卡住

这也是稳定性的一部分。

---

## 25. 为什么需要“运行参数”

你项目里有这些配置：

- `MAX_TOOL_ROUNDS`
- `TOOL_CALL_TIMEOUT`
- `LLM_CALL_TIMEOUT`
- `MAX_TOOL_OUTPUT_TO_LLM`
- `SUMMARIZE_THRESHOLD`

这些都不是装饰，它们分别对应真实风险：

### 25.1 `MAX_TOOL_ROUNDS`

防止 Worker 无限 tool loop。

### 25.2 `TOOL_CALL_TIMEOUT`

防止某个外部 API 卡死整个任务。

### 25.3 `LLM_CALL_TIMEOUT`

防止模型长时间无响应。

### 25.4 `MAX_TOOL_OUTPUT_TO_LLM`

防止工具输出太长，塞爆模型上下文。

### 25.5 `SUMMARIZE_THRESHOLD`

控制什么时候值得触发一次摘要压缩。

---

## 26. React + Vite 是什么

### 26.1 React

React 是前端 UI 框架。

适合把页面拆成可复用组件，比如：

- 登录页
- 线程列表
- 消息气泡
- 输入框
- 任务面板

### 26.2 Vite

Vite 是前端开发与构建工具。

负责：

- 启动本地前端开发服务器
- 热更新
- 打包生产版本

### 26.3 你当前前端的意义

前端不是只为了“好看”，它承担了：

- 登录注册
- 保存 token
- 维护当前 thread
- 发起聊天请求
- 实时接收流式事件
- 展示任务状态和历史线程

---

## 27. 前端里的认证流程是怎么接后端的

你现在前端已经开始进入“真实登录态”的模式了。

最典型的流程是：

1. 在 `AuthPage` 输入 email/password
2. 调 `/api/auth/login` 或 `/api/auth/register`
3. 后端返回 JWT token
4. 前端把 token 存入 localStorage
5. 后续请求带着 token 调业务接口

这就是从“匿名 UUID 模式”向“真实用户模式”的升级。

---

## 28. SSE 在前端怎么被消费

虽然浏览器有原生 `EventSource`，但那更适合 GET。

你的 `/api/chat` 是 POST，所以前端通常会：

- 用 `fetch()`
- 读取 `response.body`
- 手动解析 SSE 文本流

这就是为什么前端代码里会有：

- `ReadableStream`
- `TextDecoder`
- 逐块解析 `event:` / `data:`

---

## 29. CORS 是什么

### 29.1 为什么浏览器会拦跨域

如果前端和后端不在同一个域名/端口：

- 比如前端 `localhost:5173`
- 后端 `localhost:8000`

浏览器会认为这是跨域请求。

后端必须显式允许，浏览器才放行。

### 29.2 你项目里的 CORS

FastAPI 中间件里配置了：

- 允许来源
- 允许方法
- 允许 header

开发期通常写得宽松，生产环境要收紧。

---

## 30. Docker Compose 是什么

`docker-compose.yml` 的作用是：

- 一条命令起数据库等依赖服务

对你项目来说，它现在最主要是：

- 起 PostgreSQL

这样你不用自己手动在本机安装和管理数据库服务。

---

## 31. 这个项目体现了哪些常见工程分层思想

你现在这个项目其实很适合拿来学“后端分层”：

### 31.1 路由层

接 HTTP 请求。

### 31.2 服务层

放业务逻辑、认证、摘要等。

### 31.3 数据层

repository + SQL。

### 31.4 图执行层

LangGraph 节点和边。

### 31.5 LLM 层

模型调用工厂、结构化输出、封装。

### 31.6 Prompt 层

纯指令内容。

这说明你项目不只是“能跑”，它已经具备了比较好的学习型工程结构。

---

## 32. 如果你想继续深入，应该优先补哪些知识

最值得优先掌握的顺序我建议是：

1. HTTP 基础
2. FastAPI 路由与依赖注入
3. Pydantic 数据模型
4. JWT 与认证
5. PostgreSQL 基础、外键、索引、事务
6. async / await
7. LangGraph 的 state / node / edge / reducer
8. LLM 结构化输出
9. Tool calling
10. SSE 流式推送

---

## 33. 一句话总结每个核心技术点

- **FastAPI**：后端 API 框架，负责接请求和回响应。
- **Route / 路由**：某个 URL 由哪段代码处理。
- **HTTP 路由层**：离浏览器最近的后端入口层。
- **Pydantic**：定义数据结构并做校验。
- **Pydantic 结构化输出**：让模型按指定 schema 返回结果。
- **LangGraph**：把 AI 工作流做成图来执行。
- **AgentState**：图中所有节点共享和更新的状态。
- **Reducer**：定义状态字段如何合并。
- **Checkpointer**：把图状态持久化到数据库。
- **Prompt**：给模型的指令。
- **LLM 调用封装**：统一管理模型实例和调用方式。
- **Tool calling**：让模型调用外部函数或 API。
- **SSE**：服务器实时往前端推送事件。
- **JWT**：登录后给前端的身份凭证。
- **Repository 模式**：把数据库操作集中封装。
- **连接池**：复用数据库连接，提高性能。
- **摘要压缩**：把长对话浓缩成较短上下文。
- **React**：构建前端交互界面。
- **Vite**：前端开发服务器和构建工具。

---

## 34. 最后给你的学习建议

不要一上来试图把所有技术都一次吃透。

更有效的方法是：

1. 先看一个完整请求怎么流动
2. 再回头理解每一层为什么存在
3. 再把陌生名词和代码位置对上

比如你可以这样练：

- 从 `POST /api/chat` 开始追踪
- 看它如何进入图
- 看图如何调用 LLM
- 看 Worker 如何调用工具
- 看结果如何通过 SSE 回前端
- 看消息如何写入数据库

当你能把这条链完整讲出来时，你对这个项目的理解就已经非常扎实了。

---

## 35. 对照阅读建议

建议你把这份文档和下面这些文件对照看：

- `architecture.md`
- `backend/app/main.py`
- `backend/app/api/routes_chat.py`
- `backend/app/api/routes_auth.py`
- `backend/app/graph/state.py`
- `backend/app/graph/nodes/worker.py`
- `backend/app/llm/client.py`
- `backend/app/llm/wrapper.py`
- `backend/app/services/auth.py`
- `backend/app/services/summarization.py`
- `backend/app/db/connection.py`
- `frontend/src/App.jsx`
- `frontend/src/AuthPage.jsx`

如果你愿意，下一步我还可以继续帮你做两份配套文档：

1. 一份“按请求链路走读代码”的教程  
2. 一份“把这些技术点做成面试问答版”的笔记
