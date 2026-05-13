from __future__ import annotations

from pathlib import Path

from llama_cpp import Llama

from app.config.settings import get_settings


class LocalLlamaService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._llm: Llama | None = None

    def validate_model_path(self) -> Path:
        model_path = Path(self.settings.model_path).expanduser()
        if not model_path.is_file():
            if self.settings.allow_dev_llm_fallback:
                return model_path
            raise RuntimeError(
                "MODEL_PATH does not point to a real GGUF file. "
                f"Expected file at: {model_path}. "
                "Update .env before starting the app."
            )
        return model_path

    def load(self) -> None:
        model_path = self.validate_model_path()
        if self.settings.allow_dev_llm_fallback and not model_path.is_file():
            return
        if self._llm is None:
            self._llm = Llama(
                model_path=str(model_path),
                n_ctx=self.settings.llm_ctx_size,
                n_threads=self.settings.llm_threads,
            )

    def generate(self, prompt: str) -> str:
        model_path = Path(self.settings.model_path).expanduser()
        if self.settings.allow_dev_llm_fallback and not model_path.is_file():
            return (
                "[Developer fallback enabled] The local GGUF model was not found, "
                "so this placeholder answer was returned for development only."
            )

        if self._llm is None:
            self.load()

        assert self._llm is not None
        result = self._llm(
            prompt,
            max_tokens=self.settings.llm_max_tokens,
            temperature=self.settings.llm_temperature,
            stream=False,
            stop=["\nUser:", "\nUSER:"],
        )
        return result["choices"][0]["text"].strip()
