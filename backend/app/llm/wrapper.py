import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.llm.client import get_structured_llm
from app.llm.output_models import IntentOutput, TaskPlanOutput
from app.models.schemas import Task, TaskStatus

logger = logging.getLogger(__name__)


async def classify_intent(system_prompt: str, user_input: str) -> tuple[str, str]:
    """
    Run intent classification with structured output.

    Returns (intent, response_style).
    Falls back to ("simple_chat", "brief") if the structured call fails.
    """
    try:
        llm = get_structured_llm(IntentOutput, temperature=0)
        result: IntentOutput = await llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_input),
            ]
        )
        return result.intent, result.response_style
    except Exception as e:
        logger.warning("Intent classification failed, falling back to simple_chat: %s", e)
        return "simple_chat", "brief"


async def plan_tasks(
    system_prompt: str,
    user_input: str,
    *,
    fallback_description: str,
) -> list[Task]:
    """
    Run task planning with structured output.

    Falls back to a single task if the structured call fails or returns no tasks.
    """
    try:
        llm = get_structured_llm(TaskPlanOutput, temperature=0)
        result: TaskPlanOutput = await llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_input),
            ]
        )
        tasks = build_tasks_from_plan(result)
        if tasks:
            return tasks
    except Exception as e:
        logger.warning("Task planning failed, falling back to single task: %s", e)

    return [
        Task(
            id="task_1",
            description=fallback_description,
            dependencies=[],
            status=TaskStatus.PENDING,
        )
    ]


def build_tasks_from_plan(plan: TaskPlanOutput) -> list[Task]:
    """Convert structured planner output into the app's Task schema."""
    return [
        Task(
            id=item.id,
            description=item.description,
            dependencies=item.dependencies,
            status=TaskStatus.PENDING,
        )
        for item in plan.tasks
    ]
