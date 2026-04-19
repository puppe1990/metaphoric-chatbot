from typing import Protocol


class ChatProvider(Protocol):
    def invoke_chat(self, system_prompt: str, user_prompt: str) -> str:
        ...
