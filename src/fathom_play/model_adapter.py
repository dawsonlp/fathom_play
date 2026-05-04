"""LLM model adapter."""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel

DEFAULT_MODEL = "gemma4:e2b"


@dataclass(frozen=True)
class ModelInfo:
    provider: str
    model: str


def _detect_provider(model: str) -> str:
    if model.startswith("anthropic.claude-"):
        return "bedrock"
    if model.startswith("claude-"):
        return "anthropic"
    return "ollama"


class ModelAdapter:
    """Returns configured model clients and metadata."""

    def __init__(self, model: str = DEFAULT_MODEL):
        self.info = ModelInfo(provider=_detect_provider(model), model=model)

    def chat_model(self) -> BaseChatModel:
        if self.info.provider == "anthropic":
            from langchain_anthropic import ChatAnthropic

            # claude-opus-4-7 does not accept the temperature parameter
            kwargs: dict = {"model": self.info.model, "max_tokens": 4096}
            if not self.info.model.startswith("claude-opus-4-7"):
                kwargs["temperature"] = 0
            return ChatAnthropic(**kwargs)
        if self.info.provider == "bedrock":
            from langchain_aws import ChatBedrockConverse

            return ChatBedrockConverse(model=self.info.model, temperature=0, max_tokens=4096)
        from langchain_ollama import ChatOllama

        return ChatOllama(model=self.info.model, format="json", temperature=0)
