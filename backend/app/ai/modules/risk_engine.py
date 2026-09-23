from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict
from app.ai.base import BaseAIModule

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class RiskEngineConfig(BaseModel):
    high_risk_categories: List[str] = Field(default_factory=lambda: ["VALVE", "MOTOR", "PUMP", "COMPRESSOR"])
    medium_risk_categories: List[str] = Field(default_factory=lambda: ["PIPE", "BEARING"])
    
class RiskEngineInput(BaseModel):
    match_confidence: float
    category: str
    critical_conflicts: int
    missing_critical_fields: int

class RiskEngineOutput(BaseModel):
    risk_level: RiskLevel
    risk_score: float # 0.0 to 1.0, where 1.0 is max risk
    risk_factors: List[str]
    recommended_action: str
    version: str

class RiskEngineModule(BaseAIModule[RiskEngineInput, RiskEngineOutput, RiskEngineConfig]):
    @property
    def version(self) -> str:
        return "2.0.0"

    def get_default_config(self) -> RiskEngineConfig:
        return RiskEngineConfig()

    def process(self, input_data: RiskEngineInput) -> RiskEngineOutput:
        self.logger.info("Evaluating risk profile")
        
        factors = []
        risk_score = 0.0
        
        # Determine baseline category risk
        cat_upper = input_data.category.upper()
        is_high_risk_cat = any(c in cat_upper for c in self.config.high_risk_categories)
        is_med_risk_cat = any(c in cat_upper for c in self.config.medium_risk_categories)
        
        if is_high_risk_cat:
            factors.append("High-risk category (e.g. pressure/electrical).")
            risk_score += 0.4
        elif is_med_risk_cat:
            factors.append("Medium-risk category (e.g. mechanical components).")
            risk_score += 0.2
            
        # Missing fields penalty
        if input_data.missing_critical_fields > 0:
            factors.append(f"Missing {input_data.missing_critical_fields} critical data field(s).")
            risk_score += 0.3
            
        # Confidence penalty
        if input_data.match_confidence < 0.70:
            factors.append("Low overall match confidence.")
            risk_score += 0.3
            
        # Critical conflicts override everything
        if input_data.critical_conflicts > 0:
            factors.append(f"{input_data.critical_conflicts} critical attribute conflict(s) detected.")
            risk_score = 1.0
            
        # Clamp score
        risk_score = min(1.0, risk_score)
        
        # Map to Risk Level
        if risk_score >= 1.0 or input_data.critical_conflicts > 0:
            level = RiskLevel.CRITICAL
            action = "DOWNGRADE_TO_REVIEW"
        elif risk_score >= 0.7:
            level = RiskLevel.HIGH
            action = "DOWNGRADE_TO_REVIEW"
        elif risk_score >= 0.4:
            level = RiskLevel.MEDIUM
            action = "REQUIRE_HUMAN_APPROVAL"
        else:
            level = RiskLevel.LOW
            action = "ALLOW_AUTOMATION"
            
        return RiskEngineOutput(
            risk_level=level,
            risk_score=round(risk_score, 4),
            risk_factors=factors,
            recommended_action=action,
            version=self.version
        )
