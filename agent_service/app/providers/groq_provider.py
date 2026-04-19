from __future__ import annotations

import os
from typing import Any


class GroqProvider:
    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        self.model_name = model
        api_key = os.getenv("GROQ_API_KEY")
        try:
            from langchain.chat_models import init_chat_model

            self._chat_model: Any = init_chat_model(
                f"groq:{self.model_name}",
                api_key=api_key,
            )
        except (ModuleNotFoundError, ImportError) as exc:
            raise RuntimeError(
                "Groq support is unavailable. Install the `langchain-groq` integration "
                "package and the agent_service dependencies before creating GroqProvider."
            ) from exc
        except Exception as exc:
            if not api_key:
                raise RuntimeError("GROQ_API_KEY is not set. Set it before creating GroqProvider.") from exc
            raise

    def invoke_chat(self, system_prompt: str, user_prompt: str) -> str:
        try:
            result = self._chat_model.invoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )
        except Exception as exc:
            if "rate_limit_exceeded" in str(exc) or "429" in str(exc):
                raise RateLimitError(str(exc)) from exc
            raise
        content = getattr(result, "content", result)
        return content if isinstance(content, str) else str(content)


class RateLimitError(Exception):
    pass
