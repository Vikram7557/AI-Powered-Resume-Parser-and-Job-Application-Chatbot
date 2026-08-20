"""
Central config: loads env vars once, everything else imports from here.

Primary LLM: OpenRouter (Anthropic Messages API).
Fallback LLM: Google Gemini when OpenRouter is out of credits or down.
"""
import os

from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.environ.get(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api"
)
MODEL_NAME = os.environ.get("CLAUDE_MODEL", "anthropic/claude-sonnet-4")

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")


def _collect_gemini_keys() -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()

    def add(raw: str | None) -> None:
        if not raw:
            return
        for part in raw.replace("\n", ",").split(","):
            key = part.strip()
            if key and key not in seen:
                seen.add(key)
                keys.append(key)

    add(os.environ.get("GEMINI_API_KEYS", ""))
    numbered = []
    for name, value in os.environ.items():
        if name == "GEMINI_API_KEY" or (
            name.startswith("GEMINI_API_KEY_") and name[len("GEMINI_API_KEY_"):].isdigit()
        ):
            numbered.append((name, value))
    numbered.sort(
        key=lambda item: (
            0 if item[0] == "GEMINI_API_KEY" else 1,
            int(item[0].rsplit("_", 1)[-1]) if item[0].rsplit("_", 1)[-1].isdigit() else 0,
        )
    )
    for _, value in numbered:
        add(value)
    return keys


GEMINI_API_KEYS = _collect_gemini_keys()
# Back-compat for older imports
GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else ""

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "mysql+pymysql://root:MyPassword123@localhost:3306/job_application_chatbot",
)
APP_URL = os.environ.get("APP_URL", "http://localhost:5173")
APP_TITLE = os.environ.get("APP_TITLE", "Ava Job Assistant")
