"""Shared Ollama chat client for agent modules."""

from __future__ import annotations

from langchain_ollama import ChatOllama

from app.config import Settings, get_settings


def get_chat_model(
    settings: Settings | None = None,
    *,
    json_mode: bool = False,
) -> ChatOllama:
    settings = settings or get_settings()
    kwargs: dict = {
        "model": settings.ollama_model,
        "base_url": settings.ollama_base_url,
        "temperature": 0,
    }
    if json_mode:
        kwargs["format"] = "json"
    return ChatOllama(**kwargs)
