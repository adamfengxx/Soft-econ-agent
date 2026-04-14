from functools import lru_cache
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()  # 将 .env 写入 os.environ，供 OpenAI SDK 等第三方库直接读取


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    DATABASE_URL: str  # e.g. postgresql+psycopg://user:pass@localhost:5432/econagent
    BRAVE_API_KEY: str = ""
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 72
    FRED_API_KEY: str = ""
    ALPHA_VANTAGE_API_KEY: str = ""
    MODEL_NAME: str = "gpt-4o"
    MAX_TOOL_ROUNDS: int = 5
    TOOL_CALL_TIMEOUT: int = 30
    LLM_CALL_TIMEOUT: int = 180
    MAX_TOOL_OUTPUT_TO_LLM: int = 3000
    HITL_TIMEOUT: int = 120
    SUMMARIZE_THRESHOLD: int = 10  # 每累积多少条新消息触发一次摘要压缩

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
