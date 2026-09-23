import pytest
import numpy as np
from pydantic import ValidationError
from app.ai.embedding.provider import EmbeddingProvider
from app.ai.modules.embedding_generator import (
    EmbeddingGeneratorModule,
    EmbeddingGeneratorInput,
    EmbeddingInputData,
)

# A mock provider for fast deterministic testing
class MockDeterministicProvider(EmbeddingProvider):
    def __init__(self, dim=768):
        self.dim = dim
        
    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        # deterministic pseudo-embedding based on string length and sum of char codes
        embeddings = []
        for text in texts:
            seed = sum(ord(c) for c in text) + len(text)
            # Create a deterministic array
            np.random.seed(seed)
            emb = np.random.randn(self.dim)
            # Normalize it
            emb = emb / np.linalg.norm(emb)
            embeddings.append(emb.tolist())
        return embeddings

@pytest.fixture
def module():
    return EmbeddingGeneratorModule(provider=MockDeterministicProvider(dim=768))

def test_prevent_db_ids():
    with pytest.raises(ValidationError) as exc:
        EmbeddingInputData(
            normalized_description="Ball bearing",
            attributes={"source_material_id": "1234"}
        )
    assert "Database IDs are not allowed" in str(exc.value)
    
    with pytest.raises(ValidationError) as exc:
        EmbeddingInputData(
            normalized_description="Ball bearing",
            attributes={"id": "1234"}
        )
    assert "Database IDs are not allowed" in str(exc.value)

def test_deterministic_output(module):
    # Same input should yield exactly the same output
    item = EmbeddingInputData(
        normalized_description="6204-2RS Deep Groove Ball Bearing",
        category="Bearings",
        manufacturer="SKF"
    )
    
    input_data = EmbeddingGeneratorInput(items=[item])
    out1 = module.process(input_data)
    out2 = module.process(input_data)
    
    assert out1.embeddings[0] == out2.embeddings[0]

def test_dimension_validation():
    # Provider returns 384d, but module expects 768d
    bad_provider = MockDeterministicProvider(dim=384)
    module = EmbeddingGeneratorModule(provider=bad_provider)
    
    item = EmbeddingInputData(
        normalized_description="Test item",
    )
    input_data = EmbeddingGeneratorInput(items=[item])
    
    with pytest.raises(ValueError) as exc:
        module.process(input_data)
        
    assert "Dimension mismatch" in str(exc.value)
    assert "Expected 768" in str(exc.value)
    assert "returned 384" in str(exc.value)

def test_semantic_similarity_mock(module):
    # Tests that similarity makes sense mechanically in our mock
    # (In reality, we will manually test the real model for semantic power)
    item1 = EmbeddingInputData(normalized_description="A")
    item2 = EmbeddingInputData(normalized_description="A")
    item3 = EmbeddingInputData(normalized_description="B")
    
    input_data = EmbeddingGeneratorInput(items=[item1, item2, item3])
    out = module.process(input_data)
    
    emb1 = np.array(out.embeddings[0])
    emb2 = np.array(out.embeddings[1])
    emb3 = np.array(out.embeddings[2])
    
    # Exact match
    assert np.isclose(np.dot(emb1, emb2), 1.0)
    # Different
    assert np.dot(emb1, emb3) < 0.99
