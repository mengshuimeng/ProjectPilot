from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


DEFAULT_API_BASE = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class LLMConfig:
    enabled: bool
    api_key: str
    api_base: str
    model: str
    timeout: float

    @classmethod
    def from_env(cls) -> "LLMConfig":
        timeout_raw = os.getenv("PROJECTPILOT_TIMEOUT", "30")
        try:
            timeout = float(timeout_raw)
        except ValueError:
            timeout = 30.0

        return cls(
            enabled=_env_bool("PROJECTPILOT_LLM_ENABLED", False),
            api_key=os.getenv("PROJECTPILOT_API_KEY", "").strip(),
            api_base=os.getenv("PROJECTPILOT_API_BASE", DEFAULT_API_BASE).rstrip("/"),
            model=os.getenv("PROJECTPILOT_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
            timeout=timeout,
        )

    @property
    def available(self) -> bool:
        return self.enabled and bool(self.api_key)

    @property
    def mode_label(self) -> str:
        return "Harness + LLM" if self.available else "Rule-based"


def get_llm_status() -> dict[str, Any]:
    config = LLMConfig.from_env()
    reason = ""
    if not config.enabled:
        reason = "PROJECTPILOT_LLM_ENABLED is not true"
    elif not config.api_key:
        reason = "PROJECTPILOT_API_KEY is not configured"

    return {
        "enabled": config.enabled,
        "available": config.available,
        "mode": config.mode_label,
        "model": config.model,
        "api_base": config.api_base,
        "timeout": config.timeout,
        "reason": reason,
    }


class LLMClient:
    """Small OpenAI-compatible chat client with structured fallback errors."""

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig.from_env()

    def generate_text(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if not self.config.available:
            return {
                "ok": False,
                "content": "",
                "error": "llm_unavailable",
                "detail": "LLM is disabled or PROJECTPILOT_API_KEY is missing.",
                "fallback": True,
            }

        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        return self._post_chat_completion(payload)

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_hint: dict[str, Any] | str | None = None,
    ) -> dict[str, Any]:
        hint_text = ""
        if schema_hint:
            if isinstance(schema_hint, str):
                hint_text = schema_hint
            else:
                hint_text = json.dumps(schema_hint, ensure_ascii=False, indent=2)

        json_user_prompt = (
            f"{user_prompt}\n\n"
            "请只返回合法 JSON，不要使用 Markdown 代码块。"
        )
        if hint_text:
            json_user_prompt += f"\nJSON 结构参考：\n{hint_text}"

        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json_user_prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        result = self._post_chat_completion(payload)
        if not result.get("ok") and result.get("error") in {"http_400", "http_422"}:
            # Some OpenAI-compatible providers and reasoning models reject
            # response_format but still follow an explicit JSON-only prompt.
            payload.pop("response_format", None)
            retry_result = self._post_chat_completion(payload)
            if retry_result.get("ok"):
                retry_result["compat_retry"] = "without_response_format"
                result = retry_result

        if not result.get("ok"):
            return result

        raw = str(result.get("content", "")).strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            return {
                "ok": False,
                "content": raw,
                "error": "json_decode_error",
                "detail": str(exc),
                "fallback": True,
            }

        result["json"] = parsed
        return result

    def _post_chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.config.api_base}/chat/completions"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            return {
                "ok": False,
                "content": "",
                "error": f"http_{exc.code}",
                "detail": detail,
                "fallback": True,
            }
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            return {
                "ok": False,
                "content": "",
                "error": "network_error",
                "detail": str(exc),
                "fallback": True,
            }
        except Exception as exc:
            return {
                "ok": False,
                "content": "",
                "error": "llm_call_error",
                "detail": str(exc),
                "fallback": True,
            }

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            return {
                "ok": False,
                "content": "",
                "error": "invalid_response",
                "detail": str(exc),
                "raw": data,
                "fallback": True,
            }

        return {
            "ok": True,
            "content": content,
            "error": "",
            "detail": "",
            "model": data.get("model", self.config.model),
            "usage": data.get("usage", {}),
            "fallback": False,
        }
