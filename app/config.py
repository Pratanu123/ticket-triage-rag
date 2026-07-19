from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Default seed path works both in Docker (/app/...) and local checkout
_DEFAULT_SEED = str(Path(__file__).resolve().parent / "rag" / "seed_data")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Local Ollama (no API keys)
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_embed_model: str = "nomic-embed-text"

    database_url: str = (
        "postgresql+asyncpg://triage:triage@postgres:5432/triage"
    )

    chroma_host: str = "chromadb"
    chroma_port: int = 8000
    chroma_collection: str = "support_kb"

    seed_data_path: str = _DEFAULT_SEED
    knowledge_base_path: str = _DEFAULT_SEED

    confidence_threshold: float = 0.7
    retrieval_top_k: int = 4


@lru_cache
def get_settings() -> Settings:
    return Settings()
