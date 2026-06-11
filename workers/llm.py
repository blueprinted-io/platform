"""Shared LLM helpers for triage and extraction jobs (§11.16)."""

import json
import re
from typing import Any, cast

import httpx
import structlog

from workers.common import exc_str

log = structlog.get_logger(__name__)


async def call_llm(
    base_url: str,
    model: str,
    api_key: str,
    system: str,
    user: str,
    timeout: int,
) -> str:
    """POST a chat-completions request and return the assistant message content.

    Raises httpx.HTTPStatusError on non-2xx responses.
    """
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    async with httpx.AsyncClient() as http:
        response = await http.post(
            f"{base_url}/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
    body = response.json()
    message = body["choices"][0]["message"]
    content = message.get("content") or message.get("reasoning_content") or ""
    content = content.strip()
    # Extract content from a ```...``` fence even if preceded by preamble text
    fence_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", content, re.DOTALL)
    if fence_match:
        content = fence_match.group(1).strip()
    elif content.startswith("```"):
        content = re.sub(r"^```[a-z]*\n?", "", content)
        content = re.sub(r"\n?```$", "", content.rstrip())
    return content


def parse_llm_json(raw: str, context: str) -> dict[str, Any]:
    """Parse LLM output as JSON, falling back to json_repair on malformed output."""
    from json_repair import repair_json

    try:
        return cast(dict[str, Any], json.loads(raw))
    except json.JSONDecodeError:
        log.warning("llm_json_parse_failed", context=context, attempting="repair")
    try:
        repaired = repair_json(raw, return_objects=True)
        if isinstance(repaired, dict):
            log.info("llm_json_repaired", context=context)
            return repaired
    except Exception as exc:
        log.warning("llm_json_repair_failed", context=context, exc=exc_str(exc))
    log.error("llm_json_unparseable", context=context, raw_preview=raw[:500])
    raise ValueError(f"LLM returned unparseable JSON for {context!r}")
