import pytest
from app.ai.modules.candidate_retriever import CandidateRetrieverModule, CandidateRetrieverInput, RawVectorCandidate

@pytest.fixture
def module():
    return CandidateRetrieverModule()

@pytest.fixture
def raw_candidates():
    return [
        RawVectorCandidate(national_material_id="NAT-001", similarity_score=0.95, category="BEARING", status="ACTIVE", metadata={"name": "Ball Bearing"}),
        RawVectorCandidate(national_material_id="NAT-002", similarity_score=0.85, category="BEARING", status="REJECTED", metadata={"name": "Bad Bearing"}),
        RawVectorCandidate(national_material_id="NAT-003", similarity_score=0.70, category="VALVE", status="ACTIVE", metadata={"name": "Gate Valve"}),
        RawVectorCandidate(national_material_id="NAT-004", similarity_score=0.55, category="BEARING", status="ACTIVE", metadata={"name": "Low Match Bearing"}),
    ]

def test_status_exclusion_and_threshold(module, raw_candidates):
    # Test that REJECTED is dropped by default config and low score is dropped
    inp = CandidateRetrieverInput(raw_candidates=raw_candidates)
    out = module.process(inp)
    
    # Should only get NAT-001 and NAT-003
    assert len(out.candidates) == 2
    ids = [c.candidate_id for c in out.candidates]
    assert "NAT-001" in ids
    assert "NAT-003" in ids
    assert "NAT-002" not in ids # Dropped due to REJECTED status
    assert "NAT-004" not in ids # Dropped due to score 0.55 < 0.60

def test_category_filtering(module, raw_candidates):
    # Test filtering to just BEARING
    inp = CandidateRetrieverInput(raw_candidates=raw_candidates, category_filter="BEARING")
    out = module.process(inp)
    
    # Should only get NAT-001
    assert len(out.candidates) == 1
    assert out.candidates[0].candidate_id == "NAT-001"

def test_explicit_status_filtering(module, raw_candidates):
    # Test filtering to just ACTIVE
    inp = CandidateRetrieverInput(raw_candidates=raw_candidates, status_filter="ACTIVE")
    out = module.process(inp)
    
    assert len(out.candidates) == 2
    
def test_no_equivalence_determined(module, raw_candidates):
    # The output should strictly be candidates and similarities.
    # It should not return any 'is_match' booleans or confidence flags.
    inp = CandidateRetrieverInput(raw_candidates=raw_candidates)
    out = module.process(inp)
    
    c = out.candidates[0]
    assert hasattr(c, "candidate_id")
    assert hasattr(c, "similarity")
    assert hasattr(c, "metadata")
    assert not hasattr(c, "is_match")
    assert not hasattr(c, "confidence")
