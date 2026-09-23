import pytest
from app.ai.modules.pairwise_matcher import PairwiseMatcherModule, PairwiseMatcherInput, MatchType

def test_high_semantic_similarity_without_veto():
    matcher = PairwiseMatcherModule()
    
    # 98% semantic similarity, no veto
    input_data = PairwiseMatcherInput(
        source_attributes={"size": "2 inch"},
        candidate_attributes={"size": "2 inch"},
        semantic_similarity=0.98,
        rule_engine_veto=False
    )
    
    result = matcher.process(input_data)
    
    # High score should result in an exact match
    assert result.final_score > 0.90
    assert result.match_type == MatchType.EXACT_DUPLICATE
    assert "Engineering Veto" not in str(result.conflicts)

def test_high_semantic_similarity_with_valve_veto():
    matcher = PairwiseMatcherModule()
    
    # 98% semantic similarity, but there's a pressure class clash vetoed by the rule engine
    input_data = PairwiseMatcherInput(
        source_attributes={"pressure_class": "CL150"},
        candidate_attributes={"pressure_class": "CL300"},
        semantic_similarity=0.98,
        rule_engine_veto=True
    )
    
    result = matcher.process(input_data)
    
    # Veto must clamp score and force NOT_EQUIVALENT
    assert result.final_score <= 0.40
    assert result.match_type == MatchType.NOT_EQUIVALENT
    
    # Must report the conflict
    conflict_found = any("Engineering Veto" in c for c in result.conflicts)
    assert conflict_found, "Expected Engineering Veto to be reported in conflicts"

def test_high_semantic_similarity_with_motor_veto():
    matcher = PairwiseMatcherModule()
    
    # Motor with 415V vs 230V
    input_data = PairwiseMatcherInput(
        source_attributes={"voltage": "415V"},
        candidate_attributes={"voltage": "230V"},
        semantic_similarity=0.90,
        rule_engine_veto=True
    )
    
    result = matcher.process(input_data)
    
    assert result.final_score <= 0.40
    assert result.match_type == MatchType.NOT_EQUIVALENT

def test_high_semantic_similarity_with_pipe_veto():
    matcher = PairwiseMatcherModule()
    
    # Pipe with different schedules
    input_data = PairwiseMatcherInput(
        source_attributes={"schedule": "SCH40"},
        candidate_attributes={"schedule": "SCH80"},
        semantic_similarity=0.95,
        rule_engine_veto=True
    )
    
    result = matcher.process(input_data)
    
    assert result.final_score <= 0.40
    assert result.match_type == MatchType.NOT_EQUIVALENT
