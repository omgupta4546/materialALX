from abc import ABC, abstractmethod
from typing import List

class EmbeddingProvider(ABC):
    """
    Abstract base class for semantic embedding providers.
    """
    @abstractmethod
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate semantic embeddings for a list of text strings.
        
        Args:
            texts: List of text inputs to embed.
            
        Returns:
            List of embeddings (lists of floats), one per input text.
        """
        pass
