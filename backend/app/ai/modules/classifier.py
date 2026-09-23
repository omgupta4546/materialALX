from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from app.ai.base import BaseAIModule

class ClassifierConfig(BaseModel):
    model_name: str = "classifier-multipass-v1"
    confidence_threshold: float = 0.6
    taxonomy_mapping: Dict[str, Dict[str, str]] = Field(
        default_factory=lambda: {
            "BEARING": {"id": "MECH-BRG", "path": "Mechanical > Bearings"},
            "VALVE": {"id": "MECH-VLV", "path": "Mechanical > Valves"},
            "MOTOR": {"id": "ELEC-MTR", "path": "Electrical > Motors"},
            "PIPE": {"id": "MECH-PIP", "path": "Mechanical > Piping"},
            "PUMP": {"id": "MECH-PMP", "path": "Mechanical > Pumps"},
        }
    )

class ClassifierInput(BaseModel):
    normalized_text: str
    attributes: Dict[str, Any]
    is_approved_classification: bool = False
    current_classification_id: Optional[str] = None
    current_classification_path: Optional[str] = None

class ClassifierOutput(BaseModel):
    classification_id: Optional[str]
    classification_path: Optional[str]
    confidence: float
    model_version: str
    explanation: str
    requires_review: bool

class ClassifierModule(BaseAIModule[ClassifierInput, ClassifierOutput, ClassifierConfig]):
    @property
    def version(self) -> str:
        return "2.0.0"

    def get_default_config(self) -> ClassifierConfig:
        return ClassifierConfig()

    def process(self, input_data: ClassifierInput) -> ClassifierOutput:
        self.logger.info(f"Classifying material: {input_data.normalized_text}")
        
        # 0. Fast-path: Never overwrite approved classifications
        if input_data.is_approved_classification and input_data.current_classification_id:
            return ClassifierOutput(
                classification_id=input_data.current_classification_id,
                classification_path=input_data.current_classification_path,
                confidence=1.0,
                model_version=self.version,
                explanation="Retained approved classification. Immutable.",
                requires_review=False
            )
            
        text = input_data.normalized_text.upper()
        
        # 1. Rules-based Fast Path (High Confidence)
        # E.g., if attributes explicitly state it's a BEARING
        attr_type = str(input_data.attributes.get("type", "")).upper()
        if attr_type in self.config.taxonomy_mapping:
            mapping = self.config.taxonomy_mapping[attr_type]
            return ClassifierOutput(
                classification_id=mapping["id"],
                classification_path=mapping["path"],
                confidence=0.98,
                model_version=self.version,
                explanation=f"Rule matched explicitly via extracted type: {attr_type}.",
                requires_review=False
            )
            
        # 2. Taxonomy Lookup Path (Medium Confidence)
        # Simple keyword matching across the text against known taxonomy concepts
        for keyword, mapping in self.config.taxonomy_mapping.items():
            if keyword in text:
                return ClassifierOutput(
                    classification_id=mapping["id"],
                    classification_path=mapping["path"],
                    confidence=0.85,
                    model_version=self.version,
                    explanation=f"Taxonomy resolved via keyword lookup: {keyword}.",
                    requires_review=False
                )
                
        # 3. LLM/ML Recommendation Fallback (Stubbed)
        # Simulating a fallback process that returns low confidence
        fallback_id = "UNKNOWN-001"
        fallback_path = "Unclassified > General"
        fallback_confidence = 0.45
        
        return ClassifierOutput(
            classification_id=fallback_id,
            classification_path=fallback_path,
            confidence=fallback_confidence,
            model_version=self.version,
            explanation="Failed deterministic rules and taxonomy lookup. Fell back to ML recommendation.",
            requires_review=fallback_confidence < self.config.confidence_threshold
        )
