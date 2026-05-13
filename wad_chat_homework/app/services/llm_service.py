from __future__ import annotations

from app.llm.engine import LocalLlamaService


class LLMService:
    _service = LocalLlamaService()

    @classmethod
    def validate_or_raise(cls) -> None:
        cls._service.validate_model_path()

    @classmethod
    def preload(cls) -> None:
        cls._service.load()

    @classmethod
    def generate_reply(cls, prompt: str) -> str:
        return cls._service.generate(prompt)
