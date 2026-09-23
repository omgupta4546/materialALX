import pytest
from app.ai.modules.explanation_generator import ExplanationGeneratorModule, ExplanationGeneratorInput

def test_deterministic_explanation_generator_no_llm_hallucination():
    module = ExplanationGeneratorModule()
    
    input_data = ExplanationGeneratorInput(
        retrieval_reason="Retrieved via pgvector cosine similarity search (top-10).",
        semantic_similarity=0.95,
        attribute_matches=["size: '2 inch'"],
        attribute_conflicts=[],
        uom_compatibility="MATCH (inch)",
        classification_compatibility="MATCH",
        critical_rule_results=[],
        risk_level="LOW",
        final_confidence=0.95,
        recommended_action="ALLOW_AUTOMATION",
        rules_version="2.0.0",
        calibration_version="2.0.0"
    )
    
    output = module.process(input_data)
    
    # Assert Exact Fields
    assert output.retrieval_reason == "Retrieved via pgvector cosine similarity search (top-10)."
    assert output.semantic_similarity == 0.95
    assert output.attribute_matches == ["size: '2 inch'"]
    assert output.attribute_conflicts == []
    assert output.uom_compatibility == "MATCH (inch)"
    assert output.classification_compatibility == "MATCH"
    assert output.critical_rule_results == []
    assert output.risk_level == "LOW"
    assert output.final_confidence == 0.95
    assert output.recommendation == "ALLOW_AUTOMATION"
    
    # Assert Metadata
    assert output.model_version == "explanation-deterministic-v1"
    assert output.prompt_version == "N/A"
    assert output.rules_version == "2.0.0"
    assert output.calibration_version == "2.0.0"
    assert output.module_version == "2.0.0"
