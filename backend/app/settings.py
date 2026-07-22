import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.environ["DATABASE_URL"]
ACCESS_CODE: str = os.environ["ACCESS_CODE"]
PRODUCTION: bool = os.environ["PRODUCTION"].lower() == "true"
ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
AI_MODEL: str = "claude-opus-4-8" if PRODUCTION else "claude-haiku-4-5-20251001"
AI_THINKING: dict | None = {"type": "adaptive"} if PRODUCTION else None
AI_EFFORT: str | None = "high" if PRODUCTION else None
