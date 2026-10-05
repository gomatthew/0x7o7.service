# -*- coding: utf-8 -*-
import pytest

from src.server.ai.llm_service import llm_service, setting


@pytest.mark.parametrize("base_url, model, expected", [
    ("https://api.siliconflow.cn/v1", "Qwen/Qwen3-8B", {"max_tokens": 123, "enable_thinking": False}),
    ("https://api.siliconflow.com/v1", "Qwen/Qwen2.5-7B-Instruct", {"max_tokens": 123}),
    ("https://api.openai.com/v1", "gpt-4o-mini", None),
])
def test_provider_request_parameters(monkeypatch, base_url, model, expected):
    monkeypatch.setattr(setting, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(setting, "LLM_BASE_URL", base_url)
    monkeypatch.setattr(setting, "LLM_MODEL", model)
    monkeypatch.setattr(setting, "LLM_ENABLE_THINKING", False)
    llm = llm_service.get_llm(max_tokens=123)
    payload = llm._get_request_payload("Hello")
    if expected is not None:
        assert payload["extra_body"] == expected
        assert "max_completion_tokens" not in payload
    else:
        assert payload["max_completion_tokens"] == 123
        assert not payload.get("extra_body")
