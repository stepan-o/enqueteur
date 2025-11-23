# llm_client.py
from __future__ import annotations

import os
from typing import List, Dict, Any, Optional

from openai import OpenAI


class LLMClientError(Exception):
    """Custom error for LLM client issues."""


class LLMClient:
    """
    Thin wrapper around OpenAI's Chat Completions API for Snapshotter-style tasks.

    - Uses environment variables:
      - OPENAI_API_KEY (required)
      - OPENAI_BASE_URL (optional; for proxy/self-hosted gateways)
    """

    def __init__(
            self,
            model: str = "gpt-4.1-mini",
            temperature: float = 0.0,
            max_tokens: int = 4000,
    ) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMClientError("OPENAI_API_KEY is not set in the environment")

        base_url = os.getenv("OPENAI_BASE_URL")  # optional (e.g. for gateways)

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url or None,
        )
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def call(
            self,
            system_prompt: str,
            user_prompt: str,
            *,
            json_mode: bool = False,
            extra_messages: Optional[List[Dict[str, Any]]] = None,
    ) -> str | Dict[str, Any]:
        """
        Call the LLM with a system + user prompt.

        - If json_mode=True, uses response_format={"type": "json_object"}
          and returns parsed JSON (dict).
        - Otherwise returns the raw string content.
        """

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        if extra_messages:
            messages.extend(extra_messages)
        messages.append({"role": "user", "content": user_prompt})

        try:
            kwargs: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }

            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            resp = self.client.chat.completions.create(**kwargs)

        except Exception as e:  # you can tighten this later
            raise LLMClientError(f"OpenAI chat.completions call failed: {e}") from e

        choice = resp.choices[0]
        content = choice.message.content

        if json_mode:
            # OpenAI returns JSON as a string; let caller handle schema validation.
            import json

            try:
                return json.loads(content)
            except Exception as e:
                raise LLMClientError(f"Failed to parse JSON response: {e}\nRaw: {content}") from e

        return content
