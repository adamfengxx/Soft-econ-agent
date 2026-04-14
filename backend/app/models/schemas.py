# backend/app/models/schemas.py
from pydantic import BaseModel
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"      # 等待依赖

class Task(BaseModel):
    id: str                          # "task_1", "task_2", ...
    description: str                 # 任务描述
    dependencies: list[str] = []     # 依赖的 task_id 列表
    status: TaskStatus = TaskStatus.PENDING
    result: str | None = None        # 执行结果
    tool_calls: list[dict] = []      # 记录工具调用详情

class SSEEventType(str, Enum):
    # 意图判断
    INTENT_CLASSIFIED = "intent_classified"

    # 任务规划
    PLAN_GENERATED = "plan_generated"

    # 任务状态变更
    TASK_STATUS_UPDATE = "task_status_update"

    # Worker 逐 token 输出
    WORKER_TOKEN = "worker_token"

    # Worker 思考链（reasoning_content）
    WORKER_REASONING = "worker_reasoning"

    # 工具调用
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_RESULT = "tool_call_result"

    # 最终报告逐 token
    REPORT_TOKEN = "report_token"

    # 简单聊天逐 token
    CHAT_TOKEN = "chat_token"

    # 流程完成
    DONE = "done"

    # 错误
    ERROR = "error"