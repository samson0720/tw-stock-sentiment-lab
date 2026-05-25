from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import requests

from app.config import get_settings
from app.llm.prompts import PROMPT_VERSION, build_news_analysis_messages


@dataclass
class LLMResult:
    status: str
    model_name: str
    prompt_version: str
    raw_response: str
    data: dict[str, Any] | None = None
    error_message: str | None = None


def _extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _messages_to_prompt(messages: list[dict[str, str]]) -> str:
    return "\n\n".join(f"{message['role']}:\n{message['content']}" for message in messages)


def _rules_fallback(title: str, content: str) -> LLMResult:
    data = {
        "news_type": "other",
        "target_type": "other",
        "target": None,
        "target_name": "",
        "sentiment": "neutral",
        "confidence": 0.0,
        "reason": "LLM失敗，未做標註",
    }
    raw = json.dumps(data, ensure_ascii=False)
    return LLMResult(
        status="success",
        model_name="rules-fallback",
        prompt_version=PROMPT_VERSION,
        raw_response=raw,
        data=data,
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
        "max_tokens": 300,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    if response.status_code >= 400:
        raise RuntimeError(f"Groq HTTP {response.status_code}: {response.text[:500]}")
    body = response.json()
    raw = body["choices"][0]["message"]["content"]
    parsed = _extract_json(raw)
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
    for attempt in range(settings.llm_max_retries + 1):
        try:
            if settings.llm_provider.lower() == "groq":
                return _analyze_with_groq(title, content, model=model)
            return _analyze_with_ollama(title, content, model=model)
        except Exception as exc:
            last_error = str(exc)
            time.sleep(min(60, 2 ** attempt * 3))

    fallback = _rules_fallback(title, content)
    fallback.error_message = f"LLM failed, used fallback: {last_error or 'Unknown LLM error'}"
    return fallback
