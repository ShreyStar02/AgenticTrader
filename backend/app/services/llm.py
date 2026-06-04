"""Provider-agnostic LLM client.

Switch providers via `LLM_PROVIDER` in .env: "nvidia" | "huggingface" | "openai" | "none".
NVIDIA NIM and OpenAI share an OpenAI-compatible /chat/completions schema; HuggingFace
uses its Inference API. All calls are best-effort: any failure returns None so the
deterministic trading pipeline keeps working (LLM never gates trades).

To add a new provider, implement a `_call_<provider>` function and register it in PROVIDERS.
"""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.logging_config import get_logger

log = get_logger("llm")


def is_enabled() -> bool:
    if not settings.llm_enabled or settings.llm_provider == "none":
        return False
    key = _active_key()
    return bool(key) or settings.llm_provider == "none"


def _active_key() -> str:
    return {
        "nvidia": settings.nvidia_api_key,
        "openai": settings.openai_api_key,
        "huggingface": settings.hf_api_key,
    }.get(settings.llm_provider, "")


def _call_openai_compatible(base_url: str, key: str, system: str, prompt: str,
                            max_tokens: int, temperature: float) -> str | None:
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    with httpx.Client(timeout=settings.llm_timeout, verify=_verify()) as client:
        r = client.post(url, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()


def _call_huggingface(system: str, prompt: str, max_tokens: int, temperature: float) -> str | None:
    url = f"{settings.hf_base_url.rstrip('/')}/{settings.llm_model}"
    payload = {
        "inputs": f"{system}\n\n{prompt}",
        "parameters": {"max_new_tokens": max_tokens, "temperature": temperature,
                       "return_full_text": False},
    }
    headers = {"Authorization": f"Bearer {settings.hf_api_key}"}
    with httpx.Client(timeout=settings.llm_timeout, verify=_verify()) as client:
        r = client.post(url, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and data:
            return (data[0].get("generated_text") or "").strip()
        if isinstance(data, dict) and "generated_text" in data:
            return data["generated_text"].strip()
        return None


def _verify():
    import os

    bundle = settings.ca_bundle
    if bundle and os.path.exists(bundle):
        return bundle
    return True


def complete(prompt: str, system: str = "You are a concise financial markets analyst.",
             max_tokens: int = 320, temperature: float = 0.3) -> str | None:
    """Return an LLM completion, or None on any failure / disabled."""
    if not is_enabled():
        return None
    try:
        provider = settings.llm_provider
        if provider == "nvidia":
            return _call_openai_compatible(
                settings.nvidia_base_url, settings.nvidia_api_key, system, prompt,
                max_tokens, temperature,
            )
        if provider == "openai":
            return _call_openai_compatible(
                settings.openai_base_url, settings.openai_api_key, system, prompt,
                max_tokens, temperature,
            )
        if provider == "huggingface":
            return _call_huggingface(system, prompt, max_tokens, temperature)
        return None
    except Exception as e:  # noqa: BLE001
        log.warning("LLM (%s) call failed: %s", settings.llm_provider, e)
        return None
