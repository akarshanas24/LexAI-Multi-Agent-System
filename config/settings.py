import os
from dataclasses import dataclass


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_csv(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None:
        return default
    items = tuple(item.strip() for item in value.split(",") if item.strip())
    return items or default


@dataclass
class Settings:
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = _get_bool("DEBUG", True)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./lexai_runtime.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
    ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
    TOP_K_DOCS: int = int(os.getenv("TOP_K_DOCS", "3"))
    ENABLE_SEMANTIC_RAG: bool = _get_bool("ENABLE_SEMANTIC_RAG", True)
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    OLLAMA_ENABLED: bool = _get_bool("OLLAMA_ENABLED", True)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "mistral:latest")
    OLLAMA_FALLBACK_MODELS: tuple[str, ...] = _get_csv("OLLAMA_FALLBACK_MODELS", ("llama3:latest",))
    OLLAMA_TIMEOUT_SECONDS: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))


settings = Settings()
