import pytest
import os
from pydantic import BaseModel
from app.ai.llm.factory import LLMProviderFactory, with_retry
from app.ai.llm.providers.mock_provider import MockProvider
from app.ai.llm.providers.openai_provider import OpenAIProvider
from app.ai.llm.providers.gemini_provider import GeminiProvider

class DummySchema(BaseModel):
    dummy_key: str = "default"

def test_factory_returns_correct_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    assert isinstance(LLMProviderFactory.get_provider(), MockProvider)
    
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    assert isinstance(LLMProviderFactory.get_provider(), OpenAIProvider)
    
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    assert isinstance(LLMProviderFactory.get_provider(), GeminiProvider)

def test_mock_provider_extract_attributes():
    provider = MockProvider()
    result = provider.extract_attributes("Some text", "VALVE", DummySchema)
    
    assert isinstance(result, DummySchema)
    assert result.dummy_key == "default"

def test_mock_provider_classify():
    provider = MockProvider()
    res = provider.classify("Text", {"ID-1": "Path 1", "ID-2": "Path 2"})
    assert res == "ID-1"

def test_mock_provider_explain():
    provider = MockProvider()
    res = provider.explain_match({"some": "context"})
    assert "Mock explanation" in res

class FailsAlwaysProvider(MockProvider):
    @with_retry(max_retries=1, fallback_to_mock=True)
    def extract_attributes(self, text: str, category: str, expected_schema: type) -> BaseModel:
        raise ConnectionError("Simulated API failure")

def test_retry_fallback_to_mock():
    # If a provider fails completely, the wrapper should catch it and use MockProvider logic
    provider = FailsAlwaysProvider()
    result = provider.extract_attributes("Fail please", "TEST", DummySchema)
    
    # It should have caught the error and used MockProvider.extract_attributes, returning a default schema
    assert isinstance(result, DummySchema)
    assert result.dummy_key == "default"
