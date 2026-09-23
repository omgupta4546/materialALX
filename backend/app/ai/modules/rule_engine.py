from pydantic import BaseModel, Field
from typing import Dict, List, Any
from app.ai.base import BaseAIModule

class RuleEngineConfig(BaseModel):
    critical_attributes: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "VALVE": ["size", "pressure_class", "body_material", "end_connection"],
            "MOTOR": ["power", "voltage", "frequency"],
            "PIPE": ["diameter", "schedule", "material_grade"],
            "BEARING": ["series", "bore", "outer_diameter", "width", "seal"],
            "VLV": ["size", "pressure_class", "body_material", "end_connection"],
            "MTR": ["power", "voltage", "frequency"],
            "PIP": ["diameter", "schedule", "material_grade"],
            "BRG": ["series", "bore", "outer_diameter", "width", "seal"],
            "PMP": ["flow_rate", "head"]
        }
    )

class RuleEngineInput(BaseModel):
    category: str
    source_attributes: Dict[str, Any]
    candidate_attributes: Dict[str, Any]

class RuleEngineOutput(BaseModel):
    critical_conflicts: int
    missing_critical_fields: int
    blocks_functional_equivalence: bool
    conflict_details: List[str]
    missing_details: List[str]
    version: str

class RuleEngineModule(BaseAIModule[RuleEngineInput, RuleEngineOutput, RuleEngineConfig]):
    @property
    def version(self) -> str:
        return "2.0.0"

    def get_default_config(self) -> RuleEngineConfig:
        return RuleEngineConfig()

    def process(self, input_data: RuleEngineInput) -> RuleEngineOutput:
        self.logger.info(f"Evaluating critical rules for category {input_data.category}")
        
        critical_conflicts = 0
        missing_critical_fields = 0
        blocks_functional_equivalence = False
        conflict_details = []
        missing_details = []
        
        category_key = input_data.category.upper()
        # Fallback search if category is like MECH-VLV instead of VALVE
        matched_rules = []
        for k, v in self.config.critical_attributes.items():
            if k in category_key:
                matched_rules = v
                break
                
        if not matched_rules:
            # If no specific critical rules for this category, we just pass
            return RuleEngineOutput(
                critical_conflicts=0,
                missing_critical_fields=0,
                blocks_functional_equivalence=False,
                conflict_details=[],
                missing_details=[],
                version=self.version
            )
            
        for attr in matched_rules:
            s_val = input_data.source_attributes.get(attr)
            c_val = input_data.candidate_attributes.get(attr)
            
            if s_val is None or c_val is None:
                missing_critical_fields += 1
                missing_details.append(f"Missing critical field: {attr}")
                # Missing a critical field doesn't automatically block equivalence, 
                # but it elevates risk.
            else:
                s_str = str(s_val).strip().lower()
                c_str = str(c_val).strip().lower()
                if s_str != c_str:
                    critical_conflicts += 1
                    conflict_details.append(f"Critical conflict on {attr}: '{s_str}' != '{c_str}'")
                    blocks_functional_equivalence = True
                    
        return RuleEngineOutput(
            critical_conflicts=critical_conflicts,
            missing_critical_fields=missing_critical_fields,
            blocks_functional_equivalence=blocks_functional_equivalence,
            conflict_details=conflict_details,
            missing_details=missing_details,
            version=self.version
        )
