"""LLM model adapter."""

from __future__ import annotations

from dataclasses import dataclass

from langchain_ollama import ChatOllama

DEFAULT_MODEL = "gemma4:e2b"


@dataclass(frozen=True)
class ModelInfo:
    provider: str
    model: str


class ModelAdapter:
    """Returns configured model clients and metadata."""

    def __init__(self, model: str = DEFAULT_MODEL):
        if model != DEFAULT_MODEL:
            raise ValueError(f"Only {DEFAULT_MODEL!r} is supported in the first implementation")
        self.info = ModelInfo(provider="ollama", model=model)

    def chat_model(self) -> ChatOllama:
        return ChatOllama(model=self.info.model, format="json", temperature=0)
