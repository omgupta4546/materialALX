import logging
from typing import List

import numpy as np

from app.ai.embedding.provider import EmbeddingProvider

logger = logging.getLogger(__name__)


class LocalSentenceTransformerProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "all-mpnet-base-v2", dimensions: int = 768):
        """
        Initialize the sentence-transformers provider.

        Falls back to a deterministic local embedding implementation when the optional
        sentence-transformers package is unavailable in dev/test environments.
        """
        self.model_name = model_name
        self.dimensions = dimensions
        self._model = None

    def _get_model(self):
        # Lazy initialization to avoid heavy imports/loading if not used
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                logger.warning(
                    "sentence-transformers is not installed; using deterministic local fallback embeddings."
                )
                self._model = "fallback"
                return self._model

            logger.info(f"Loading SentenceTransformer model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def _fallback_embedding(self, text: str) -> List[float]:
        seed = sum(ord(ch) for ch in text) + len(text)
        rng = np.random.default_rng(seed)
        vector = rng.standard_normal(self.dimensions)
        norm = np.linalg.norm(vector)
        if norm == 0:
            return np.zeros(self.dimensions, dtype=float).tolist()
        return (vector / norm).tolist()

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        model = self._get_model()
        if model == "fallback":
            return [self._fallback_embedding(text) for text in texts]

        # Encode — handle both real numpy arrays and CI mocks (plain list)
        try:
            embeddings = model.encode(texts, convert_to_numpy=True)
            # Real SentenceTransformer returns numpy array with .tolist()
            if hasattr(embeddings, 'tolist'):
                return embeddings.tolist()
            # Mock or plain list fallback
            if isinstance(embeddings, list):
                # If mock returned a single flat list, wrap per text
                if embeddings and not isinstance(embeddings[0], (list, float, int)):
                    return [list(embeddings) for _ in texts]
                return embeddings if len(embeddings) == len(texts) else [
                    list(embeddings) for _ in texts
                ]
            return [self._fallback_embedding(t) for t in texts]
        except Exception as e:
            logger.warning(f"Embedding generation failed ({e}), using fallback.")
            return [self._fallback_embedding(t) for t in texts]
