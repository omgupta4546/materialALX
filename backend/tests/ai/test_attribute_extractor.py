import pytest
from app.ai.modules.attribute_extractor import AttributeExtractorModule, AttributeExtractorInput

pytestmark = pytest.mark.no_db

@pytest.fixture
def module():
    return AttributeExtractorModule()

def test_extract_bearing(module):
    # Test BEARING category
    inp = AttributeExtractorInput(normalized_text="BEARING 6205 2RS 25X52X15 MM", category_context="BEARING")
    out = module.process(inp)
    
    attrs = {a.attribute: a for a in out.attributes}
    
    assert "series" in attrs
    assert attrs["series"].value == "6205"
    
    assert "seal" in attrs
    assert attrs["seal"].value == "2RS"
    
    assert "bore" in attrs
    assert attrs["bore"].value == "25"
    assert attrs["bore"].unit == "MM"
    
    assert "outer_diameter" in attrs
    assert attrs["outer_diameter"].value == "52"
    
    assert "width" in attrs
    assert attrs["width"].value == "15"

def test_extract_valve(module):
    # Test VALVE category
    inp = AttributeExtractorInput(normalized_text="VALVE BALL 2 IN 150# SS", category_context="VALVE")
    out = module.process(inp)
    
    attrs = {a.attribute: a for a in out.attributes}
    
    assert "type" in attrs
    assert attrs["type"].value == "BALL"
    
    assert "size" in attrs
    assert attrs["size"].value == "2"
    assert attrs["size"].unit == "IN"
    
    assert "pressure_class" in attrs
    assert attrs["pressure_class"].value == "150#"
    
    assert "body_material" in attrs
    assert attrs["body_material"].value == "SS"

def test_extract_motor(module):
    # Test MOTOR category
    inp = AttributeExtractorInput(normalized_text="MOTOR 5.5 KW 400 V 50 HZ 3 PHASE 1450 RPM TEFC", category_context="MOTOR")
    out = module.process(inp)
    
    attrs = {a.attribute: a for a in out.attributes}
    
    assert "power" in attrs
    assert attrs["power"].value == "5.5"
    assert attrs["power"].unit == "KW"
    
    assert "voltage" in attrs
    assert attrs["voltage"].value == "400"
    
    assert "frequency" in attrs
    assert attrs["frequency"].value == "50"
    assert attrs["frequency"].unit == "HZ"
    
    assert "phase" in attrs
    assert attrs["phase"].value == "3"
    
    assert "rpm" in attrs
    assert attrs["rpm"].value == "1450"
    
    assert "enclosure" in attrs
    assert attrs["enclosure"].value == "TEFC"

def test_extract_pipe(module):
    # Test PIPE category
    inp = AttributeExtractorInput(normalized_text="PIPE 1/2 IN SCH 40 CS", category_context="PIPE")
    out = module.process(inp)
    
    attrs = {a.attribute: a for a in out.attributes}
    
    assert "diameter" in attrs
    assert attrs["diameter"].value == "1/2"
    assert attrs["diameter"].unit == "IN"
    
    assert "schedule" in attrs
    assert attrs["schedule"].value == "SCH 40"
    
    assert "material_grade" in attrs
    assert attrs["material_grade"].value == "CS"

def test_missing_values_not_invented(module):
    # Test missing values are not hallucinated
    inp = AttributeExtractorInput(normalized_text="VALVE GATE 150#", category_context="VALVE")
    out = module.process(inp)
    
    attrs = {a.attribute: a for a in out.attributes}
    
    assert "type" in attrs
    assert attrs["type"].value == "GATE"
    assert "pressure_class" in attrs
    assert attrs["pressure_class"].value == "150#"
    
    # Missing size, material, etc should NOT be present
    assert "size" not in attrs
    assert "body_material" not in attrs
