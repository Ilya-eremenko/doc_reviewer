from app.schemas.enums import Provider
from providers.base import AnalysisProviderResult, ProviderAdapter, ProviderRunRequest
from providers.anthropic_compatible import AnthropicCompatibleAdapter
from providers.hermes import HermesAdapter
from providers.openai_compatible import OpenAICompatibleAdapter


class MockProviderAdapter(ProviderAdapter):
    def run(self, request: ProviderRunRequest) -> AnalysisProviderResult:
        result = request.run_parameters.get("mock_provider_result")
        if not result:
            raise RuntimeError("mock_provider_result is required for local test provider execution")
        return AnalysisProviderResult(**result)


def get_provider_adapter(provider: Provider, run_parameters: dict | None = None) -> ProviderAdapter:
    if run_parameters and "mock_provider_result" in run_parameters:
        return MockProviderAdapter()
    if provider == Provider.OPENAI_COMPATIBLE:
        return OpenAICompatibleAdapter()
    if provider == Provider.ANTHROPIC_COMPATIBLE:
        return AnthropicCompatibleAdapter()
    if provider == Provider.HERMES:
        return HermesAdapter()
    raise RuntimeError(f"unsupported_provider:{provider}")
