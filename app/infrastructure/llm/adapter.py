"""LLM adapter using OpenAI for ideation, ranking, and markdown generation."""

import json
import re
from typing import TYPE_CHECKING, Any, Optional

from app.logging_config import get_logger

if TYPE_CHECKING:
    from app.config import Settings

logger = get_logger(__name__)


class LLMError(Exception):
    """Raised when an LLM call fails."""


class LLMAdapter:
    """Wraps OpenAI API calls for the POC Factory."""

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        self.model = model
        self._api_key = api_key
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazily initialize the OpenAI client."""
        import openai  # type: ignore[import-untyped]

        if self._client is None:
            self._client = openai.OpenAI(api_key=self._api_key)
        return self._client

    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> str:
        """Make a completion request to the OpenAI API."""
        client = self._get_client()

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        logger.debug("llm_request", provider="openai", model=self.model, prompt_len=len(prompt))

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            text = response.choices[0].message.content or ""
            logger.debug("llm_response", response_len=len(text))
            return text
        except Exception as e:
            logger.error("llm_error", provider="openai", error=str(e))
            raise LLMError(f"LLM completion failed: {e}") from e

    def complete_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> Any:
        """Make a completion request expecting JSON output."""
        response = self.complete(prompt, system=system, max_tokens=max_tokens, temperature=0.2)
        json_str = _extract_json(response)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error("json_parse_error", response_preview=response[:200])
            raise LLMError(f"Failed to parse LLM JSON response: {e}") from e

    async def complete_async(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> str:
        """Async version of complete()."""
        import openai  # type: ignore[import-untyped]

        client = openai.AsyncOpenAI(api_key=self._api_key)

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise LLMError(f"Async LLM completion failed: {e}") from e

    async def complete_json_async(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> Any:
        """Async version of complete_json()."""
        response = await self.complete_async(
            prompt, system=system, max_tokens=max_tokens, temperature=0.2
        )
        json_str = _extract_json(response)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise LLMError(f"Failed to parse async LLM JSON response: {e}") from e


def _extract_json(text: str) -> str:
    """Extract JSON from a text response that may include prose."""
    code_fence_match = re.search(r"```(?:json)?\s*\n([\s\S]*?)\n```", text)
    if code_fence_match:
        return code_fence_match.group(1).strip()

    json_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if json_match:
        return json_match.group(1)

    return text.strip()


def create_llm_adapter(settings: "Settings") -> "LLMAdapter":
    """Return an LLM adapter configured from settings.

    Raises LLMError if OPENAI_API_KEY is not set.
    """
    if settings.openai_api_key:
        logger.info("llm_provider_selected", provider="openai", model=settings.openai_model)
        return LLMAdapter(api_key=settings.openai_api_key, model=settings.openai_model)
    raise LLMError(
        "No LLM API key configured. Set OPENAI_API_KEY in your .env file."
    )
