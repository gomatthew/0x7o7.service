# -*- coding: utf-8 -*-
"""Small async client for the published Document to Decision Dify Workflow."""

import json
from collections.abc import AsyncIterator

import httpx

from src.configs import get_setting

setting = get_setting()


class DifyWorkflowError(RuntimeError):
    """Raised when Dify rejects or fails a workflow run."""


def workflow_url() -> str:
    base_url = setting.DIFY_SERVER_URL.rstrip("/")
    if not base_url:
        raise DifyWorkflowError("The Dify workflow URL is not configured")
    return f"{base_url}/workflows/run"


async def stream_document_analysis(
    *, inputs: dict[str, str], user: str
) -> AsyncIterator[dict]:
    """Yield normalized text and completion events from Dify's SSE response."""
    if not setting.DIFY_DEMO_SECRET_KEY:
        raise DifyWorkflowError("The Dify demo workflow key is not configured")

    timeout = httpx.Timeout(
        connect=min(setting.LLM_REQUEST_TIMEOUT, 20),
        read=setting.LLM_STREAM_TIMEOUT,
        write=setting.LLM_REQUEST_TIMEOUT,
        pool=setting.LLM_REQUEST_TIMEOUT,
    )
    headers = {
        "Authorization": f"Bearer {setting.DIFY_DEMO_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": inputs,
        "response_mode": "streaming",
        "user": user,
    }

    workflow_finished = False
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", workflow_url(), headers=headers, json=payload) as response:
            if response.status_code >= 400:
                await response.aread()
                raise DifyWorkflowError(f"Dify workflow returned HTTP {response.status_code}")

            async for raw_line in response.aiter_lines():
                if not raw_line.startswith("data:"):
                    continue
                raw_data = raw_line[5:].strip()
                if not raw_data:
                    continue
                try:
                    event = json.loads(raw_data)
                except json.JSONDecodeError:
                    continue

                event_type = event.get("event")
                data = event.get("data") or {}
                if event_type == "text_chunk":
                    text = data.get("text")
                    if isinstance(text, str) and text:
                        yield {"event": "text", "text": text}
                elif event_type == "workflow_finished":
                    workflow_finished = True
                    if data.get("status") != "succeeded":
                        raise DifyWorkflowError("Dify workflow did not complete successfully")
                    outputs = data.get("outputs") or {}
                    answer = outputs.get("answer")
                    yield {
                        "event": "finished",
                        "answer": answer if isinstance(answer, str) else "",
                        "workflow_run_id": event.get("workflow_run_id") or data.get("id"),
                    }
                elif event_type in {"error", "workflow_failed"}:
                    raise DifyWorkflowError("Dify workflow reported an execution error")

    if not workflow_finished:
        raise DifyWorkflowError("Dify workflow stream ended before completion")
