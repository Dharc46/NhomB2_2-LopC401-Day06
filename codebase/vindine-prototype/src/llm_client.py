"""Minimal LLM client for VinDine. Supports Groq (default) and Gemini."""

import logging
import os
import time

logger = logging.getLogger("vindine.llm")


class LLMError(Exception):
    """Raised when an LLM call fails."""


def is_llm_available() -> bool:
    return bool(os.getenv("VINDINE_LLM_KEY"))


def _get_provider() -> str:
    return os.getenv("VINDINE_LLM_PROVIDER", "groq")


def _call_groq(*, system: str, user: str, json_mode: bool, api_key: str) -> str:
    """Call Groq API (OpenAI-compatible)."""
    try:
        from openai import OpenAI
    except ImportError as e:
        raise LLMError("openai package not installed") from e

    model = os.getenv("VINDINE_LLM_MODEL", "llama-3.3-70b-versatile")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )

    kwargs: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.1,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content


def _call_gemini(*, system: str, user: str, json_mode: bool, api_key: str) -> str:
    """Call Google Gemini API."""
    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        raise LLMError("google-genai package not installed") from e

    model = os.getenv("VINDINE_LLM_MODEL", "gemini-2.0-flash")

    client = genai.Client(api_key=api_key)

    config_kwargs: dict = {
        "temperature": 0.1,
        "system_instruction": system,
    }
    if json_mode:
        config_kwargs["response_mime_type"] = "application/json"

    config = types.GenerateContentConfig(**config_kwargs)

    response = client.models.generate_content(
        model=model,
        contents=user,
        config=config,
    )
    return response.text


def call_llm(*, system: str, user: str, json_mode: bool = False) -> str:
    """Call configured LLM provider. Returns raw text or JSON string.

    Raises LLMError on any failure.
    """
    api_key = os.getenv("VINDINE_LLM_KEY")
    if not api_key:
        raise LLMError("VINDINE_LLM_KEY not set")

    provider = _get_provider()
    start = time.time()

    try:
        if provider == "gemini":
            result = _call_gemini(system=system, user=user, json_mode=json_mode, api_key=api_key)
        else:
            result = _call_groq(system=system, user=user, json_mode=json_mode, api_key=api_key)

        duration_ms = (time.time() - start) * 1000
        model = os.getenv("VINDINE_LLM_MODEL", "llama-3.3-70b-versatile" if provider == "groq" else "gemini-2.0-flash")
        logger.info(
            "LLM call completed in %.0fms | provider=%s | model=%s | response_length=%d",
            duration_ms,
            provider,
            model,
            len(result),
        )
        return result

    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        logger.warning("LLM call failed after %.0fms: %s", duration_ms, e)
        raise LLMError(str(e)) from e
