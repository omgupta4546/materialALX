import pytest
from pydantic import ValidationError
from app.ai.modules.embedding_generator import EmbeddingGeneratorModule, EmbeddingGeneratorInput, EmbeddingInputData

@pytest.fixture
def module():
    return EmbeddingGeneratorModule()

def test_semantic_text_construction(module):
    inp = EmbeddingInputData(
        category="VALVE",
        normalized_description="VALVE BALL 2 IN 150# SS",
        attributes={"size": "2 IN", "type": "BALL", "body_material": "SS"},
        manufacturer="MOCK_MFG",
        manufacturer_part_number="MOCK-123"
    )
    
    text = module._construct_embedding_text(inp)
    
    assert "Category: VALVE" in text
    assert "Description: VALVE BALL 2 IN 150# SS" in text
    assert "Attributes: size: 2 IN, type: BALL, body_material: SS" in text
    assert "Manufacturer: MOCK_MFG" in text
    assert "MPN: MOCK-123" in text

def test_optional_fields_omitted(module):
    inp = EmbeddingInputData(
        normalized_description="VALVE BALL 2 IN 150# SS"
    )
    
    text = module._construct_embedding_text(inp)
    
    assert "Description: VALVE BALL 2 IN 150# SS" in text
    assert "Category:" not in text
    assert "Attributes:" not in text
    assert "Manufacturer:" not in text
    assert "MPN:" not in text

def test_db_ids_rejected():
    with pytest.raises(ValidationError) as exc:
        EmbeddingInputData(
            normalized_description="TEST",
            material_id="12345"
        )
    assert "Database IDs are not allowed" in str(exc.value)
    
    with pytest.raises(ValidationError) as exc2:
        EmbeddingInputData(
            normalized_description="TEST",
            id="12345"
        )
    assert "Database IDs are not allowed" in str(exc2.value)

def test_batch_processing(module):
    inp = EmbeddingGeneratorInput(
        items=[
            EmbeddingInputData(normalized_description="ITEM 1"),
            EmbeddingInputData(normalized_description="ITEM 2"),
            EmbeddingInputData(normalized_description="ITEM 3")
        ]
    )
    
    out = module.process(inp)
    
    assert len(out.embeddings) == 3
    assert len(out.embeddings[0]) == module.config.dimensions
    assert isinstance(out.embeddings[0], list)
    assert isinstance(out.embeddings[0][0], float)
    assert out.model_version == module.version
