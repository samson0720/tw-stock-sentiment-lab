import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


def _load_env_file() -> dict[str, str]:
    env_path = BASE_DIR / ".env"
    values: dict[str, str] = {}
    if not env_path.exists():
        return values
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _env(name: str, default: str | None = None) -> str | None:
    file_values = _load_env_file()
    return os.getenv(name, file_values.get(name, default))


@dataclass(frozen=True)
class Settings:
    database_path: Path
    ollama_base_url: str
    ollama_model: str
    groq_api_key: str | None
    groq_base_url: str
    groq_model: str
    llm_provider: str
    llm_prompt_version: str
    llm_request_sleep_seconds: float
    llm_max_retries: int
    finmind_token: str | None


@lru_cache
def get_settings() -> Settings:
    database_path = Path(_env("DATABASE_PATH", str(BASE_DIR / "data" / "twstock_sentiment.db")) or "")
    if not database_path.is_absolute():
        database_path = BASE_DIR / database_path

    return Settings(
        database_path=database_path,
        ollama_base_url=_env("OLLAMA_BASE_URL", "http://localhost:11434") or "http://localhost:11434",
        ollama_model=_env("OLLAMA_MODEL", "qwen2.5:7b") or "qwen2.5:7b",
        groq_api_key=_env("GROQ_API_KEY"),
        groq_base_url=_env("GROQ_BASE_URL", "https://api.groq.com/openai/v1") or "https://api.groq.com/openai/v1",
        groq_model=_env("GROQ_MODEL", "llama-3.3-70b-versatile") or "llama-3.3-70b-versatile",
        llm_provider=(_env("LLM_PROVIDER", "groq") or "groq").lower(),
        llm_prompt_version=_env("LLM_PROMPT_VERSION", "twstock-news-v6") or "twstock-news-v6",
        llm_request_sleep_seconds=float(_env("LLM_REQUEST_SLEEP_SECONDS", "2.0") or "2.0"),
        llm_max_retries=int(_env("LLM_MAX_RETRIES", "4") or "4"),
        finmind_token=_env("FINMIND_TOKEN"),
    )
