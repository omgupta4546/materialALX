import math
from pydantic import BaseModel
from typing import Dict, Any
from app.ai.base import BaseAIModule

class ConfidenceCalculatorConfig(BaseModel):
    calibration_version: str = "platt-logistic-mock-v1"
    logistic_a: float = 10.0
    logistic_b: float = -7.5

class ConfidenceCalculatorInput(BaseModel):
    raw_final_score: float

class ConfidenceCalculatorOutput(BaseModel):
    calibrated_confidence: float
    calibration_version: str
    version: str

class ConfidenceCalculatorModule(BaseAIModule[ConfidenceCalculatorInput, ConfidenceCalculatorOutput, ConfidenceCalculatorConfig]):
    @property
    def version(self) -> str:
        return "1.0.0"

    def get_default_config(self) -> ConfidenceCalculatorConfig:
        return ConfidenceCalculatorConfig()

    def process(self, input_data: ConfidenceCalculatorInput) -> ConfidenceCalculatorOutput:
        self.logger.info("Calibrating raw match score")
        
        # Logistic calibration: P = 1 / (1 + exp(-(A*score + B)))
        # For A=10, B=-7.5: 
        # score=1.0 -> 1 / (1 + exp(-2.5)) ~ 0.92
        # score=0.8 -> 1 / (1 + exp(-0.5)) ~ 0.62
        # score=0.5 -> 1 / (1 + exp(2.5)) ~ 0.07
        
        raw = input_data.raw_final_score
        exponent = -((self.config.logistic_a * raw) + self.config.logistic_b)
        
        try:
            calibrated = 1.0 / (1.0 + math.exp(exponent))
        except OverflowError:
            calibrated = 0.0
            
        return ConfidenceCalculatorOutput(
            calibrated_confidence=round(calibrated, 4),
            calibration_version=self.config.calibration_version,
            version=self.version
        )
