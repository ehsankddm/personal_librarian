"""LLM Gateway Client

Async client for the local LLM Gateway (OpenAI-compatible) described in
external_docs/LLM_GATEWAY_API.md. Provides simple chat and reasoning helpers.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypedDict

import aiohttp


class LLMResult(TypedDict):
    raw_text: str
    parsed_json: dict | None
    finish_reason: str
    tokens_in: int
    tokens_out: int
    model_name: str
    elapsed_ms: int


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Fetch environment variable at call time (supports late load via dotenv)."""
    return os.getenv(key, default)


def _redact(text: str) -> str:
    """Redact obvious secrets/paths to keep logs safe in Phase 2."""
    if not text:
        return text
    # Basic email and file-path redaction
    text = re.sub(r"[\w\.-]+@[\w\.-]+", "<redacted:email>", text)
    text = re.sub(r"(/[^\s]+)+", "/<redacted:path>", text)
    text = re.sub(r"[A-Za-z]:\\\\[^\s]+", "<redacted:winpath>", text)
    return text


class LLMClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout_sec: Optional[int] = None,
    ) -> None:
        # Resolve defaults at init time to pick up .env loaded later
        resolved_base = base_url or _env("LLM_BASE", "http://localhost:7766")
        resolved_api_key = api_key if api_key is not None else _env("LLM_API_KEY")
        resolved_model = default_model or _env("LLM_MODEL_ALIAS", "gpt-4o-mini")
        resolved_timeout = (
            timeout_sec if timeout_sec is not None else int(_env("LLM_TIMEOUT", "60"))
        )

        self.base_url = resolved_base.rstrip("/")
        self.api_key = resolved_api_key
        self.default_model = resolved_model
        self.timeout_sec = resolved_timeout

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        extra: Optional[Dict[str, Any]] = None,
    ) -> LLMResult:
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if extra:
            payload["extra"] = extra

        url = f"{self.base_url}/v1/chat/completions"

        start = asyncio.get_event_loop().time()
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout_sec)) as sess:
            async with sess.post(url, headers=self._headers(), json=payload) as resp:
                resp.raise_for_status()
                data = await resp.json()

        elapsed_ms = int((asyncio.get_event_loop().time() - start) * 1000)
        choice = (data.get("choices") or [{}])[0]
        message = (choice.get("message") or {})
        content = message.get("content", "")
        finish_reason = choice.get("finish_reason", "unknown")

        result: LLMResult = {
            "raw_text": content or "",
            "parsed_json": None,
            "finish_reason": finish_reason,
            "tokens_in": 0,
            "tokens_out": 0,
            "model_name": data.get("model", payload["model"]),
            "elapsed_ms": elapsed_ms,
        }
        return result

    async def generate_reasoning(
        self,
        context_bundle: Dict[str, Any],
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> LLMResult:
        """Call the gateway with a system + user message containing the bundle.

        This method does not enforce JSON-mode server-side; callers must validate.
        """
        # Keep the bundle compact-ish to avoid huge payloads
        safe_bundle = {
            "agent_identity": context_bundle.get("agent_identity", {}),
            "incoming_message": context_bundle.get("incoming_message", {}),
            "candidate_actions": context_bundle.get("candidate_actions", []),
            "policies": context_bundle.get("policies", {}),
            "preferences": context_bundle.get("preferences", {}),
        }
        user_content = (
            "You are assisting routing. Given the bundle below, return ONLY a compact JSON object.\n"
            "BUNDLE:\n" + json.dumps(safe_bundle, ensure_ascii=False)
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        result = await self.chat(messages, model=model, temperature=temperature, max_tokens=max_tokens)

        # Best-effort JSON extraction
        text = result["raw_text"].strip()
        parsed: Optional[dict] = None
        try:
            # Strip code fences if present
            if text.startswith("```"):
                text = re.sub(r"^```(json)?", "", text).strip()
                text = re.sub(r"```$", "", text).strip()
            # Extract the first {...} block
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                parsed = json.loads(m.group(0))
            else:
                parsed = json.loads(text)
        except Exception:
            parsed = None

        result["parsed_json"] = parsed
        # Redaction for any subsequent logging handled by caller/telemetry
        result["raw_text"] = _redact(result["raw_text"])
        return result
