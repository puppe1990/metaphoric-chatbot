from __future__ import annotations

import os
from typing import Any


class NvidiaProvider:
    def __init__(self, model: str = "meta/llama-3.1-70b-instruct"):
        self.model_name = model
        api_key = os.getenv("NVIDIA_API_KEY")
        try:
            from langchain.chat_models import init_chat_model

            self._chat_model: Any = init_chat_model(
                self.model_name,
                model_provider="nvidia",
                api_key=api_key,
            )
        except (ModuleNotFoundError, ImportError) as exc:
            raise RuntimeError(
                "NVIDIA NIM support is unavailable. "
                "Install `langchain-nvidia-ai-endpoints` before creating NvidiaProvider."
            ) from exc
        except Exception as exc:
            if not api_key:
                raise RuntimeError("NVIDIA_API_KEY is not set. Set it before creating NvidiaProvider.") from exc
            raise

    def invoke_chat(self, system_prompt: str, user_prompt: str) -> str:
        result = self._chat_model.invoke(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        content = getattr(result, "content", result)
        return content if isinstance(content, str) else str(content)
