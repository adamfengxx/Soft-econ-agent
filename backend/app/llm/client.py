from collections.abc import Sequence
from typing import TypeVar

from langchain_core.runnables import RunnableBinding
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.config import settings

StructuredModelT = TypeVar("StructuredModelT", bound=BaseModel)


def get_chat_llm(*, temperature: float = 0, streaming: bool = False) -> ChatOpenAI:
    """Create a base ChatOpenAI client with shared project defaults."""
    return ChatOpenAI(
        model=settings.MODEL_NAME,
        temperature=temperature,
        streaming=streaming,
        timeout=settings.LLM_CALL_TIMEOUT,
    )


def get_streaming_llm(*, temperature: float = 0) -> ChatOpenAI:
    """Create a streaming chat client for token-by-token responses."""
    return get_chat_llm(temperature=temperature, streaming=True)


def get_tool_llm(
    tools: Sequence[BaseTool],
    *,
    temperature: float = 0,
) -> RunnableBinding:
    """Create a chat client already bound to tools."""
    return get_chat_llm(temperature=temperature).bind_tools(list(tools))


def get_structured_llm(
    output_model: type[StructuredModelT],
    *,
    temperature: float = 0,
) -> RunnableBinding:
    """Create a chat client configured for structured output."""
    return get_chat_llm(temperature=temperature).with_structured_output(output_model)
