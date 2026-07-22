from langchain_anthropic import ChatAnthropic
from pydantic import SecretStr

from app.settings import AI_EFFORT, AI_MODEL, AI_THINKING, ANTHROPIC_API_KEY


def get_llm(timeout: int = 30) -> ChatAnthropic:
    return ChatAnthropic(
        model_name=AI_MODEL,
        api_key=SecretStr(ANTHROPIC_API_KEY),
        timeout=timeout,
        stop=None,
        thinking=AI_THINKING,
        effort=AI_EFFORT,
    )
