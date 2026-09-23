from typing import Dict, Any, Type, TypeVar
from pydantic import BaseModel
from app.ai.llm.provider import LLMProvider

T = TypeVar('T', bound=BaseModel)

class MockProvider(LLMProvider):
    """
    Mock LLM Provider for local development and CI testing.
    Returns deterministic, safe outputs without making network calls.
    """
    
    def extract_attributes(self, text: str, category: str, expected_schema: Type[T]) -> T:
        # Mock logic: returns empty dict initialized to schema defaults
        # or parses some basic mock data if requested.
        return expected_schema.model_validate({})
        
    def classify(self, text: str, taxonomy: Dict[str, str]) -> str:
        # Return first key from taxonomy if available, otherwise a default
        if taxonomy:
            return list(taxonomy.keys())[0]
        return "UNKNOWN-001"
        
    def generate_canonical_description(self, attributes: Dict[str, Any]) -> str:
        parts = [f"{k.upper()}: {v}" for k, v in attributes.items()]
        return " | ".join(parts) if parts else "UNKNOWN ITEM"
        
    def explain_match(self, context: Dict[str, Any]) -> str:
        return "Mock explanation: Based on provided attributes, items appear to match."
