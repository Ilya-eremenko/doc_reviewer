from types import SimpleNamespace

import pytest

from app.core.config import get_settings
from app.schemas.enums import Provider
from providers.anthropic_compatible import AnthropicCompatibleAdapter
from providers.base import ProviderRunRequest
from providers.hermes import HermesAdapter
from providers.openai_compatible import OpenAICompatibleAdapter


def test_openai_compatible_adapter_normalizes_chat_completion():
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"summary":"ok"}'))],
                usage=SimpleNamespace(prompt_tokens=11, completion_tokens=22),
                model_dump_json=lambda: '{"raw":true}',
            )

    class FakeClient:
        chat = SimpleNamespace(completions=FakeCompletions())

    adapter = OpenAICompatibleAdapter(client_factory=lambda **_: FakeClient())

    result = adapter.run(_request(Provider.OPENAI_COMPATIBLE, api_key="sk-test", base_url="https://openai.test/v1"))

    assert captured["model"] == "model-test"
    assert captured["messages"][0]["content"] == "Prompt"
    assert captured["response_format"]["type"] == "json_schema"
    assert result.structured_text == '{"summary":"ok"}'
    assert result.raw_output == '{"raw":true}'
    assert result.input_tokens == 11
    assert result.output_tokens == 22


def test_anthropic_compatible_adapter_normalizes_message_response():
    captured = {}

    class FakeMessages:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                content=[SimpleNamespace(text='{"summary":"claude"}')],
                usage=SimpleNamespace(input_tokens=33, output_tokens=44),
                model_dump_json=lambda: '{"raw":"claude"}',
            )

    class FakeClient:
        messages = FakeMessages()

    adapter = AnthropicCompatibleAdapter(client_factory=lambda **_: FakeClient())

    result = adapter.run(_request(Provider.ANTHROPIC_COMPATIBLE, api_key="anthropic-test"))

    assert captured["model"] == "model-test"
    assert captured["max_tokens"] == 6000
    assert result.structured_text == '{"summary":"claude"}'
    assert result.input_tokens == 33
    assert result.output_tokens == 44


def test_hermes_adapter_returns_provider_unavailable_when_disabled(monkeypatch):
    monkeypatch.setenv("HERMES_ENABLED", "false")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="provider_unavailable"):
        HermesAdapter(post=lambda *_, **__: None).run(_request(Provider.HERMES, api_key=None))
    get_settings.cache_clear()


def test_hermes_adapter_normalizes_http_response(monkeypatch):
    monkeypatch.setenv("HERMES_ENABLED", "true")
    get_settings.cache_clear()

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "structured_text": '{"summary":"hermes"}',
                "usage": {"input_tokens": 55, "output_tokens": 66},
                "latency_ms": 77,
            }

    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    result = HermesAdapter(post=fake_post).run(_request(Provider.HERMES, api_key=None, base_url="http://hermes.test"))

    assert captured["url"] == "http://hermes.test/v1/analysis"
    assert captured["json"]["prompt"] == "Prompt"
    assert result.structured_text == '{"summary":"hermes"}'
    assert result.input_tokens == 55
    assert result.output_tokens == 66
    assert result.latency_ms == 77
    get_settings.cache_clear()


def _request(provider: Provider, *, api_key: str | None, base_url: str | None = None) -> ProviderRunRequest:
    return ProviderRunRequest(
        provider=provider,
        model="model-test",
        api_key=api_key,
        base_url=base_url,
        prompt="Prompt",
        response_schema={"type": "object"},
        run_parameters={},
    )
