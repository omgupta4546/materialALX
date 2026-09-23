import pytest
from app.ai.modules.pairwise_matcher import PairwiseMatcherModule, PairwiseMatcherInput, MatchType

@pytest.fixture
def module():
    return PairwiseMatcherModule()

def test_exact_duplicate(module):
    inp = PairwiseMatcherInput(
        source_attributes={"size": "2", "type": "BALL"},
        candidate_attributes={"size": "2", "type": "BALL"},
        source_manufacturer="MOCK",
        candidate_manufacturer="MOCK",
        source_mpn="123",
        candidate_mpn="123",
        source_uom_dimension="LENGTH",
        candidate_uom_dimension="LENGTH",
        semantic_similarity=0.98
    )
    out = module.process(inp)
    
    assert out.match_type == MatchType.EXACT_DUPLICATE
    assert out.final_score >= 0.95
    assert len(out.conflicts) == 0

def test_uom_clash_forces_review(module):
    # Even with high semantic match, a UOM clash should force review
    inp = PairwiseMatcherInput(
        source_attributes={"type": "BALL"},
        candidate_attributes={"type": "BALL"},
        source_uom_dimension="LENGTH",
        candidate_uom_dimension="MASS", # Clash! Length vs Mass
        semantic_similarity=0.95
    )
    out = module.process(inp)
    
    assert out.match_type == MatchType.REQUIRES_ENGINEERING_REVIEW
    assert any("UOM Dimension Clash" in c for c in out.conflicts)

def test_attribute_conflicts_force_review(module):
    inp = PairwiseMatcherInput(
        source_attributes={"size": "2", "material": "CS"},
        candidate_attributes={"size": "4", "material": "SS"}, # 2 conflicts
        semantic_similarity=0.85
    )
    out = module.process(inp)
    
    assert out.match_type == MatchType.REQUIRES_ENGINEERING_REVIEW
    assert len(out.conflicts) >= 2

def test_functionally_equivalent(module):
    inp = PairwiseMatcherInput(
        source_attributes={"size": "2", "type": "BALL"},
        candidate_attributes={"size": "2", "type": "BALL"},
        source_manufacturer="BRAND A",
        candidate_manufacturer="BRAND B", # Different brands, but same spec
        semantic_similarity=0.88
    )
    out = module.process(inp)
    
    assert out.match_type in [MatchType.FUNCTIONALLY_EQUIVALENT, MatchType.NEAR_DUPLICATE]
    assert any("Manufacturer mismatch" in c for c in out.conflicts)
