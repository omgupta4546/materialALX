import pytest
from app.ai.modules.rule_engine import RuleEngineModule, RuleEngineInput
from app.ai.modules.risk_engine import RiskEngineModule, RiskEngineInput, RiskLevel

@pytest.fixture
def rule_engine():
    return RuleEngineModule()

@pytest.fixture
def risk_engine():
    return RiskEngineModule()

def test_sneaky_valve_clash(rule_engine, risk_engine):
    # Test 1: Sneaky Valve (high semantic, pressure clash) -> CRITICAL
    rule_in = RuleEngineInput(
        category="VALVE",
        source_attributes={"size": "2 IN", "pressure_class": "150#", "body_material": "SS"},
        candidate_attributes={"size": "2 IN", "pressure_class": "300#", "body_material": "SS"}
    )
    rule_out = rule_engine.process(rule_in)
    
    # Assert rule engine catches the 300# != 150# clash
    assert rule_out.critical_conflicts == 1
    assert rule_out.blocks_functional_equivalence is True
    
    risk_in = RiskEngineInput(
        match_confidence=0.95, # Very high semantic similarity
        category="VALVE",
        critical_conflicts=rule_out.critical_conflicts,
        missing_critical_fields=rule_out.missing_critical_fields
    )
    risk_out = risk_engine.process(risk_in)
    
    # Despite 0.95 confidence, risk MUST be CRITICAL because of the clash
    assert risk_out.risk_level == RiskLevel.CRITICAL
    assert risk_out.recommended_action == "DOWNGRADE_TO_REVIEW"
    assert risk_out.risk_score == 1.0

def test_missing_motor_data(rule_engine, risk_engine):
    # Test 2: Missing Motor Data -> Elevated Risk
    rule_in = RuleEngineInput(
        category="MOTOR",
        source_attributes={"power": "5 HP", "frequency": "50 HZ"},
        # Missing 'voltage' which is a critical field for motors
        candidate_attributes={"power": "5 HP", "frequency": "50 HZ"}
    )
    rule_out = rule_engine.process(rule_in)
    
    assert rule_out.critical_conflicts == 0
    assert rule_out.missing_critical_fields >= 1
    assert rule_out.blocks_functional_equivalence is False # Missing doesn't strictly block, but elevates risk
    
    risk_in = RiskEngineInput(
        match_confidence=0.88,
        category="MOTOR", # High risk category
        critical_conflicts=rule_out.critical_conflicts,
        missing_critical_fields=rule_out.missing_critical_fields
    )
    risk_out = risk_engine.process(risk_in)
    
    # High risk category + missing field = HIGH risk overall
    assert risk_out.risk_level == RiskLevel.HIGH
    assert risk_out.recommended_action == "DOWNGRADE_TO_REVIEW"

def test_safe_bearing_match(rule_engine, risk_engine):
    # Test 3: Safe Match -> LOW risk
    rule_in = RuleEngineInput(
        category="BEARING",
        source_attributes={"series": "6205", "seal": "2RS", "bore": "25", "outer_diameter": "52", "width": "15"},
        candidate_attributes={"series": "6205", "seal": "2RS", "bore": "25", "outer_diameter": "52", "width": "15"}
    )
    rule_out = rule_engine.process(rule_in)
    
    assert rule_out.critical_conflicts == 0
    assert rule_out.missing_critical_fields == 0
    assert rule_out.blocks_functional_equivalence is False
    
    risk_in = RiskEngineInput(
        match_confidence=0.95,
        category="BEARING", # Medium risk category
        critical_conflicts=rule_out.critical_conflicts,
        missing_critical_fields=rule_out.missing_critical_fields
    )
    risk_out = risk_engine.process(risk_in)
    
    # Medium risk category + perfect match + no missing fields -> LOW risk
    assert risk_out.risk_level == RiskLevel.LOW
    assert risk_out.recommended_action == "ALLOW_AUTOMATION"
