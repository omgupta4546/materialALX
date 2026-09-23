import pytest
from app.ai.modules.rule_engine import RuleEngineModule, RuleEngineInput, RuleEngineConfig

pytestmark = pytest.mark.no_db

def test_valve_pressure_clash():
    engine = RuleEngineModule(RuleEngineConfig())
    # Same valve, different pressure (CL150 vs CL300)
    out = engine.process(RuleEngineInput(
        category="VALVE",
        source_attributes={"type": "GATE VALVE", "size": "6IN", "pressure_class": "150#", "body_material": "CS"},
        candidate_attributes={"type": "GATE VALVE", "size": "6IN", "pressure_class": "300#", "body_material": "CS"}
    ))
    assert out.blocks_functional_equivalence is True
    assert out.critical_conflicts == 1
    assert any("pressure_class" in d for d in out.conflict_details)

def test_motor_voltage_clash():
    engine = RuleEngineModule(RuleEngineConfig())
    # Same motor, different voltage (415V vs 440V)
    out = engine.process(RuleEngineInput(
        category="MOTOR",
        source_attributes={"power": "15KW", "voltage": "415V", "frequency": "50HZ"},
        candidate_attributes={"power": "15KW", "voltage": "440V", "frequency": "50HZ"}
    ))
    assert out.blocks_functional_equivalence is True
    assert out.critical_conflicts == 1
    assert any("voltage" in d for d in out.conflict_details)

def test_pipe_grade_clash():
    engine = RuleEngineModule(RuleEngineConfig())
    # Same pipe, different grade (SS vs CS)
    out = engine.process(RuleEngineInput(
        category="PIPE",
        source_attributes={"diameter": "4IN", "schedule": "SCH40", "material_grade": "SS"},
        candidate_attributes={"diameter": "4IN", "schedule": "SCH40", "material_grade": "CS"}
    ))
    assert out.blocks_functional_equivalence is True
    assert out.critical_conflicts == 1
    assert any("material_grade" in d for d in out.conflict_details)

def test_bearing_dimension_clash():
    engine = RuleEngineModule(RuleEngineConfig())
    # Same bearing, different dimensions (simulating bore conflict)
    out = engine.process(RuleEngineInput(
        category="BEARING",
        source_attributes={"series": "6205", "seal": "2RS", "bore": "25MM"},
        candidate_attributes={"series": "6205", "seal": "2RS", "bore": "30MM"}
    ))
    assert out.blocks_functional_equivalence is True
    assert out.critical_conflicts == 1
    assert any("bore" in d for d in out.conflict_details)

def test_missing_critical_attributes():
    engine = RuleEngineModule(RuleEngineConfig())
    # Missing size for a valve
    out = engine.process(RuleEngineInput(
        category="VALVE",
        source_attributes={"type": "GATE VALVE", "pressure_class": "150#"},
        candidate_attributes={"type": "GATE VALVE", "pressure_class": "150#"}
    ))
    # Missing attribute does not immediately block equivalence, but raises missing count
    assert out.missing_critical_fields >= 1
    assert any("size" in d for d in out.missing_details)
