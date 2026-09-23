import pytest
from app.ai.modules.confidence_calculator import ConfidenceCalculatorModule, ConfidenceCalculatorInput
from app.ai.modules.explanation_generator import ExplanationGeneratorModule, ExplanationGeneratorInput
from app.ai.modules.pairwise_matcher import MatchType

@pytest.fixture
def calc_module():
    return ConfidenceCalculatorModule()

@pytest.fixture
def exp_module():
    return ExplanationGeneratorModule()

def test_logistic_calibration_dampens_score(calc_module):
    # A raw score of 0.8 should be dampened by the logistic curve (A=10, B=-7.5 -> exp(-0.5) -> ~0.62)
    inp1 = ConfidenceCalculatorInput(raw_final_score=0.8)
    out1 = calc_module.process(inp1)
    
    assert out1.calibrated_confidence < 0.65
    assert out1.calibrated_confidence > 0.60
    assert out1.calibration_version == "platt-logistic-mock-v1"
    
    # A perfect score 1.0 should map highly (A=10, B=-7.5 -> exp(2.5) -> ~0.92)
    inp2 = ConfidenceCalculatorInput(raw_final_score=1.0)
    out2 = calc_module.process(inp2)
    
    assert out2.calibrated_confidence > 0.90
    assert out2.calibrated_confidence < 0.95

def test_explanation_generator_schema_and_flags(exp_module):
    inp = ExplanationGeneratorInput(
        positive_evidence=["Matches exact MPN"],
        negative_evidence=["Manufacturer differs"],
        conflicts=["UOM Clash"],
        calibrated_confidence=0.62,
        risk_level="CRITICAL",
        recommended_action="DOWNGRADE_TO_REVIEW",
        match_type=MatchType.REQUIRES_ENGINEERING_REVIEW,
        rules_version="rules-v2",
        calibration_version="calib-v1"
    )
    
    out = exp_module.process(inp)
    
    # Schema check
    assert out.positive_evidence == ["Matches exact MPN"]
    assert out.conflicts == ["UOM Clash"]
    assert out.confidence == 0.62
    assert out.risk == "CRITICAL"
    
    # Traceability Metadata check
    assert out.model_version == "explanation-deterministic-v1"
    assert out.prompt_version == "N/A"
    assert out.rules_version == "rules-v2"
    assert out.calibration_version == "calib-v1"
    
    # Boolean logic check (CRITICAL risk + < 0.7 confidence -> Requires Review)
    assert out.requires_human_review is True
    
    # Anti-hallucination recommendation check
    assert "REQUIRES_ENGINEERING_REVIEW" in out.recommendation
    assert "DOWNGRADE_TO_REVIEW" in out.recommendation
