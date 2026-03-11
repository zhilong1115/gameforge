"""LLM client abstraction.

Provides a unified interface for calling different LLM providers.
Used by the Producer to generate execution plans.
"""

from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Abstract LLM client — swap providers freely."""

    @abstractmethod
    def complete(
        self,
        prompt: str,
        system: str = "",
        model: str | None = None,
        json_mode: bool = False,
        max_tokens: int = 4096,
    ) -> str:
        """Send a prompt and get a completion.
        
        Args:
            prompt: User message.
            system: System message.
            model: Override the default model.
            json_mode: Request JSON output format.
            max_tokens: Max response tokens.
            
        Returns:
            The model's text response.
        """
        ...


class AnthropicClient(LLMClient):
    """Anthropic Claude client."""

    def __init__(self, api_key: str | None = None, default_model: str = "claude-opus-4-6"):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.default_model = default_model

    def complete(
        self,
        prompt: str,
        system: str = "",
        model: str | None = None,
        json_mode: bool = False,
        max_tokens: int = 4096,
    ) -> str:
        response = self.client.messages.create(
            model=model or self.default_model,
            max_tokens=max_tokens,
            system=system if system else anthropic.NOT_GIVEN,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text


class OpenAIClient(LLMClient):
    """OpenAI GPT client."""

    def __init__(self, api_key: str | None = None, default_model: str = "gpt-4o"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.default_model = default_model

    def complete(
        self,
        prompt: str,
        system: str = "",
        model: str | None = None,
        json_mode: bool = False,
        max_tokens: int = 4096,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": model or self.default_model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
