from abc import ABC, abstractmethod


class ILLMPort(ABC):
    """Abstract port for language model interactions."""

    @abstractmethod
    async def generate(self, prompt: str, model: str, max_tokens: int = 512) -> str:
        """Generate a completion for a given prompt and model."""
        ...

    @abstractmethod
    async def query(self, system_prompt: str, user_message: str, model: str) -> str:
        """Query the model with a system prompt and a user message."""
        ...