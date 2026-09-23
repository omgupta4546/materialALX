from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Dict, Any, Type, TypeVar

T = TypeVar('T', bound=BaseModel)

class LLMProvider(ABC):
    """
    Abstract base class for all LLM interactions in the Antigravity Material matching pipeline.
    Ensures that the core orchestration is completely decoupled from any specific AI vendor.
    """
    
    @abstractmethod
    def extract_attributes(self, text: str, category: str, expected_schema: Type[T]) -> T:
        """
        Extracts structured attributes from a raw description text.
        Must return an instance of `expected_schema`.
        """
        pass
        
    @abstractmethod
    def classify(self, text: str, taxonomy: Dict[str, str]) -> str:
        """
        Classifies a raw description into a provided taxonomy.
        Returns the taxonomy ID.
        """
        pass
        
    @abstractmethod
    def generate_canonical_description(self, attributes: Dict[str, Any]) -> str:
        """
        Generates a clean, canonical engineering description from structured attributes.
        """
        pass
        
    @abstractmethod
    def explain_match(self, context: Dict[str, Any]) -> str:
        """
        Generates a human-readable explanation of why two items match or conflict.
        Strict anti-hallucination policies must be applied in the provider implementation.
        """
        pass
