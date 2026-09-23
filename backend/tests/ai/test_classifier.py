import pytest
from app.ai.modules.classifier import ClassifierModule, ClassifierInput

@pytest.fixture
def module():
    return ClassifierModule()

def test_classifier_rules_fast_path(module):
    # Test that extracted type attribute takes highest priority
    inp = ClassifierInput(
        normalized_text="SOME RANDOM TEXT",
        attributes={"type": "BEARING"}
    )
    out = module.process(inp)
    
    assert out.classification_id == "MECH-BRG"
    assert out.confidence == 0.98
    assert out.requires_review is False
    assert "Rule matched explicitly" in out.explanation

def test_classifier_taxonomy_lookup(module):
    # Test that keyword lookup works if attributes don't match
    inp = ClassifierInput(
        normalized_text="LARGE CENTRIFUGAL PUMP 50HP",
        attributes={}
    )
    out = module.process(inp)
    
    assert out.classification_id == "MECH-PMP"
    assert out.confidence == 0.85
    assert out.requires_review is False
    assert "Taxonomy resolved via keyword" in out.explanation

def test_classifier_fallback_requires_review(module):
    # Test that unknown inputs fall back and require review
    inp = ClassifierInput(
        normalized_text="MYSTERY COMPONENT V1",
        attributes={}
    )
    out = module.process(inp)
    
    assert out.classification_id == "UNKNOWN-001"
    assert out.confidence < 0.6
    assert out.requires_review is True
    assert "ML recommendation" in out.explanation

def test_classifier_protects_approved(module):
    # Test the most critical constraint: immutability of approved categories
    inp = ClassifierInput(
        normalized_text="BEARING",
        attributes={"type": "BEARING"},
        is_approved_classification=True,
        current_classification_id="CUSTOM-BRG",
        current_classification_path="Custom > Bearing"
    )
    out = module.process(inp)
    
    # Even though text says BEARING, it should NOT override CUSTOM-BRG
    assert out.classification_id == "CUSTOM-BRG"
    assert out.classification_path == "Custom > Bearing"
    assert out.confidence == 1.0
    assert out.requires_review is False
    assert "Immutable" in out.explanation
