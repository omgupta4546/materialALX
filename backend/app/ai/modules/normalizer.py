import re
from pydantic import BaseModel, Field
from app.ai.base import BaseAIModule
from typing import Dict, Optional

class NormalizerConfig(BaseModel):
    abbreviations: Dict[str, str] = Field(
        default_factory=lambda: {
            "BRG": "BEARING",
            "BRNG": "BEARING",
            "DIA": "DIAMETER",
            "SS": "STAINLESS STEEL",
            "CS": "CARBON STEEL",
            "GALV": "GALVANIZED",
            "PCS": "EA",
            "EACH": "EA",
        }
    )
    engineering_patterns: Dict[str, str] = Field(
        default_factory=lambda: {
            r"(\d+(?:\.\d+)?(?:/\d+)?)\s*(?:\"|''|IN|INCH)": r"\1 IN",
            r"(\d+(?:\.\d+)?)\s*(?:MM|MILLIMETER)": r"\1 MM",
        }
    )

class NormalizerInput(BaseModel):
    raw_text: str

class NormalizerOutput(BaseModel):
    normalized_text: str
    version: str
    method: str

class NormalizerModule(BaseAIModule[NormalizerInput, NormalizerOutput, NormalizerConfig]):
    @property
    def version(self) -> str:
        return "1.0.0"
        
    def get_default_config(self) -> NormalizerConfig:
        return NormalizerConfig()
        
    def process(self, input_data: NormalizerInput) -> NormalizerOutput:
        self.logger.info(f"Normalizing text: {input_data.raw_text}")
        
        if not input_data.raw_text:
            return NormalizerOutput(normalized_text="", version=self.version, method="Regex & Dictionary")
            
        text = input_data.raw_text.upper()
        # Clean punctuation
        text = re.sub(r'[,;_\-]', ' ', text)
        
        # Engineering patterns
        for pattern, replacement in self.config.engineering_patterns.items():
            text = re.sub(pattern, replacement, text)
            
        # Dictionary replacements
        words = text.split()
        normalized_words = []
        for word in words:
            clean_word = word.rstrip('.')
            if clean_word in self.config.abbreviations:
                normalized_words.append(self.config.abbreviations[clean_word])
            else:
                normalized_words.append(word)
                
        final_text = " ".join(normalized_words)
        
        return NormalizerOutput(
            normalized_text=final_text, 
            version=self.version, 
            method="Regex & Dictionary"
        )
