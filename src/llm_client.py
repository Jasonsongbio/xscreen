"""LLM client wrapper supporting multiple providers via LiteLLM.

Abstracts away provider differences (DeepSeek, Claude, GLM, etc.) and
adds JSON schema validation + retry logic.

Usage:
    client = LLMClient(provider="deepseek", model="deepseek-chat", api_key="...")
    entries = client.complete_json(system="...", user="...")
"""
import json
import logging
from typing import Any

import litellm

logger = logging.getLogger(__name__)

# Suppress litellm's verbose info logging
litellm.suppress_debug_info = True


class LLMClient:
    """Multi-provider LLM client via LiteLLM."""

    # Map xscreen provider names to LiteLLM model prefixes
    PROVIDER_PREFIX = {
        "deepseek": "deepseek",
        "anthropic": "claude",
        "glm": "zhipu",
        "openai": "openai",
        "qwen": "dashscope",
    }

    def __init__(
        self,
        provider: str,
        model: str,
        api_key: str,
        base_url: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        max_retries: int = 3,
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries

    def _litellm_model_string(self) -> str:
        """Convert (provider, model) to LiteLLM model string.

        LiteLLM uses 'provider/model' format (e.g., 'deepseek/deepseek-chat').
        """
        prefix = self.PROVIDER_PREFIX.get(self.provider, self.provider)
        if self.model.startswith(f"{prefix}/"):
            return self.model
        return f"{prefix}/{self.model}"

    def _call_once(self, system: str, user: str) -> str:
        """Single LLM call, returns raw content string.

        Raises whatever exception litellm.completion raises.
        """
        kwargs = {
            "model": self._litellm_model_string(),
            "api_key": self.api_key,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.base_url:
            kwargs["api_base"] = self.base_url

        response = litellm.completion(**kwargs)
        return response.choices[0].message.content

    def _strip_code_fence(self, content: str) -> str:
        """Remove markdown code fences if present (```json ... ```)."""
        content = content.strip()
        if content.startswith("```"):
            # Remove first line (the ```json or ``` line)
            lines = content.split("\n", 1)
            if len(lines) > 1:
                content = lines[1]
            # Remove trailing ```
            if content.rstrip().endswith("```"):
                content = content.rstrip()[:-3]
        return content.strip()

    def complete_json(self, system: str, user: str) -> list[dict[str, Any]]:
        """Call LLM and parse JSON array response.

        Retries up to max_retries times on JSON parse failure or API errors.
        Returns [] if all retries fail.

        Args:
            system: System prompt.
            user: User prompt (typically the formatted extraction prompt).

        Returns:
            List of dicts parsed from LLM's JSON array response.
            Single dict responses are wrapped in a list.
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                content = self._call_once(system, user)
                content = self._strip_code_fence(content)
                parsed = json.loads(content)

                if isinstance(parsed, list):
                    return parsed
                if isinstance(parsed, dict):
                    return [parsed]
                logger.warning(
                    f"Attempt {attempt}/{self.max_retries}: "
                    f"unexpected JSON type {type(parsed).__name__}"
                )
            except json.JSONDecodeError as e:
                logger.warning(
                    f"Attempt {attempt}/{self.max_retries}: JSON parse failed: {e}"
                )
            except Exception as e:
                logger.warning(
                    f"Attempt {attempt}/{self.max_retries}: LLM call failed: {type(e).__name__}: {e}"
                )

        logger.error(f"All {self.max_retries} attempts failed; returning empty list")
        return []
