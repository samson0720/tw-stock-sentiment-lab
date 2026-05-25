from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any

import requests

from app.config import get_settings
from app.llm.prompts import PROMPT_VERSION, build_news_analysis_messages


class RateLimitError(RuntimeError):
    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


@dataclass
class LLMResult:
    status: str
    model_name: str
    prompt_version: str
    raw_response: str
    data: dict[str, Any] | None = None
    error_message: str | None = None


def _json_loads(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        fixed = re.sub(r"\\u(?![0-9a-fA-F]{4})", r"\\\\u", text)
        if fixed != text:
            return json.loads(fixed)
        raise


def _extract_json(text: str) -> dict[str, Any]:
    try:
        return _json_loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return _json_loads(text[start : end + 1])
        raise


def _messages_to_prompt(messages: list[dict[str, str]]) -> str:
    return "\n\n".join(f"{message['role']}:\n{message['content']}" for message in messages)


def _rules_fallback(title: str, content: str) -> LLMResult:
    data = {
        "news_type": "other",
        "target_type": "other",
        "target": None,
        "target_name": "",
        "targets": [],
        "sentiment": "neutral",
        "confidence": 0.0,
        "reason": "LLM失敗，未做標註",
    }
    raw = json.dumps(data, ensure_ascii=False)
    return LLMResult(
        status="failed",
        model_name="rules-fallback",
        prompt_version=PROMPT_VERSION,
        raw_response=raw,
        data=None,
    )


def _analyze_with_ollama(title: str, content: str, model: str | None = None) -> LLMResult:
    settings = get_settings()
    model_name = model or settings.ollama_model
    payload = {
        "model": model_name,
        "prompt": _messages_to_prompt(build_news_analysis_messages(title=title, content=content)),
        "stream": False,
        "format": "json",
    }
    response = requests.post(f"{settings.ollama_base_url.rstrip('/')}/api/generate", json=payload, timeout=120)
    response.raise_for_status()
    body = response.json()
    raw = body.get("response", "")
    parsed = _extract_json(raw)
    return LLMResult(
        status="success",
        model_name=model_name,
        prompt_version=PROMPT_VERSION,
        raw_response=raw,
        data=parsed,
    )


def _analyze_with_groq(title: str, content: str, model: str | None = None) -> LLMResult:
    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is required when llm_provider=groq")

    model_name = model or settings.groq_model
    url = f"{settings.groq_base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model_name,
        "messages": build_news_analysis_messages(title=title, content=content),
        "temperature": 0,
        "max_completion_tokens": 1000,
    }
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        retry_seconds: float | None = None
        if retry_after:
            try:
                retry_seconds = float(retry_after)
            except ValueError:
                retry_seconds = None
        if retry_seconds is None:
            match = re.search(r"try again in ([0-9.]+)s", response.text, flags=re.IGNORECASE)
            if match:
                retry_seconds = float(match.group(1))
        raise RateLimitError(f"Groq HTTP 429: {response.text[:500]}", retry_after=retry_seconds)
    if response.status_code >= 400:
        raise RuntimeError(f"Groq HTTP {response.status_code}: {response.text[:500]}")
    body = response.json()
    raw = body["choices"][0]["message"]["content"]
    try:
        parsed = _extract_json(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON response: {exc}; raw={raw[:500]}") from exc
    return LLMResult(
        status="success",
        model_name=model_name,
        prompt_version=PROMPT_VERSION,
        raw_response=raw,
        data=parsed,
    )


def analyze_news(title: str, content: str, model: str | None = None) -> LLMResult:
    settings = get_settings()
    last_error: str | None = None
    max_attempts = max(settings.llm_max_retries + 1, 1)
    max_rate_limit_attempts = max(max_attempts, 4)
    attempt = 0
    while attempt < max_rate_limit_attempts:
        try:
            if settings.llm_provider.lower() == "groq":
                return _analyze_with_groq(title, content, model=model)
            return _analyze_with_ollama(title, content, model=model)
        except RateLimitError as exc:
            last_error = str(exc)
            attempt += 1
            if attempt >= max_rate_limit_attempts:
                break
            time.sleep(max(1.0, min(60.0, exc.retry_after or (2 ** attempt * 3))))
        except Exception as exc:
            last_error = str(exc)
            attempt += 1
            if attempt >= max_attempts:
                break
            time.sleep(min(60, 2 ** attempt * 3))

    fallback = _rules_fallback(title, content)
    fallback.error_message = f"LLM failed, used fallback: {last_error or 'Unknown LLM error'}"
    return fallback
