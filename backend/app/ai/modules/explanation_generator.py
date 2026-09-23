from pydantic import BaseModel, ConfigDict
from typing import List, Optional

from app.ai.base import BaseAIModule
from app.ai.modules.pairwise_matcher import MatchType


class ExplanationGeneratorConfig(BaseModel):
    model_version: str = "explanation-deterministic-v1"
    prompt_version: str = "N/A"


class ExplanationGeneratorInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    positive_evidence: List[str] = []
    negative_evidence: List[str] = []
    conflicts: List[str] = []
    calibrated_confidence: float = 0.0
    risk_level: str = "UNKNOWN"
    recommended_action: str = "REVIEW"
    match_type: Optional[MatchType] = None
    rules_version: str = ""
    calibration_version: str = ""

    retrieval_reason: str = ""
    semantic_similarity: float = 0.0
    attribute_matches: List[str] = []
    attribute_conflicts: List[str] = []
    uom_compatibility: str = "MATCH (or NA)"
    classification_compatibility: str = "MATCH"
    critical_rule_results: List[str] = []
    final_confidence: float = 0.0


class ExplanationGeneratorOutput(BaseModel):
    positive_evidence: List[str] = []
    negative_evidence: List[str] = []
    conflicts: List[str] = []
    confidence: float
    risk: str
    recommendation: str
    requires_human_review: bool = False

    retrieval_reason: str = ""
    semantic_similarity: float = 0.0
    attribute_matches: List[str] = []
    attribute_conflicts: List[str] = []
    uom_compatibility: str = ""
    classification_compatibility: str = ""
    critical_rule_results: List[str] = []
    risk_level: str = ""
    final_confidence: float = 0.0

    model_version: str
    prompt_version: str
    rules_version: str
    calibration_version: str
    module_version: str = ""


class ExplanationGeneratorModule(BaseAIModule[ExplanationGeneratorInput, ExplanationGeneratorOutput, ExplanationGeneratorConfig]):
    @property
    def version(self) -> str:
        return "2.0.0"

    def get_default_config(self) -> ExplanationGeneratorConfig:
        return ExplanationGeneratorConfig()

    def process(self, input_data: ExplanationGeneratorInput) -> ExplanationGeneratorOutput:
        self.logger.info("Generating deterministic explanation payload")

        positive_evidence = list(input_data.positive_evidence or input_data.attribute_matches or [])
        conflicts = list(input_data.conflicts or input_data.attribute_conflicts or [])
        confidence = input_data.calibrated_confidence or input_data.final_confidence or 0.0
        risk = input_data.risk_level
        recommendation = input_data.recommended_action

        if input_data.match_type is not None:
            recommendation = f"{input_data.match_type.value} | {recommendation}"

        requires_human_review = (risk == "CRITICAL" and confidence < 0.7) or (input_data.match_type == MatchType.REQUIRES_ENGINEERING_REVIEW) or "REVIEW" in recommendation.upper()

        module_version = input_data.rules_version or self.version
        return ExplanationGeneratorOutput(
            positive_evidence=positive_evidence,
            negative_evidence=list(input_data.negative_evidence or []),
            conflicts=conflicts,
            confidence=confidence,
            risk=risk,
            recommendation=recommendation,
            requires_human_review=requires_human_review,
            retrieval_reason=input_data.retrieval_reason,
            semantic_similarity=input_data.semantic_similarity,
            attribute_matches=list(input_data.attribute_matches or []),
            attribute_conflicts=list(input_data.attribute_conflicts or []),
            uom_compatibility=input_data.uom_compatibility,
            classification_compatibility=input_data.classification_compatibility,
            critical_rule_results=list(input_data.critical_rule_results or []),
            risk_level=input_data.risk_level,
            final_confidence=input_data.final_confidence,
            model_version=self.config.model_version,
            prompt_version=self.config.prompt_version,
            rules_version=input_data.rules_version,
            calibration_version=input_data.calibration_version,
            module_version=module_version,
        )
