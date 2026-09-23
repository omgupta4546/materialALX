import json
import os
from typing import Dict, Any, Type, TypeVar
from pydantic import BaseModel

# Use the new google-genai SDK (google.generativeai is deprecated)
try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
except ImportError:
    genai = None
    _GENAI_AVAILABLE = False

from app.ai.llm.provider import LLMProvider

T = TypeVar('T', bound=BaseModel)

class GeminiProvider(LLMProvider):
    """
    Gemini implementation utilizing Structured Outputs for JSON adherence.
    Requires GEMINI_API_KEY environment variable.
    Falls back to mock behaviour if API key is not set.
    """

    def __init__(self):
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.is_configured = False

    def _ensure_configured(self):
        if not self.is_configured:
            if _GENAI_AVAILABLE:
                genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
            self.is_configured = True

    def _has_api_key(self) -> bool:
        key = os.environ.get("GEMINI_API_KEY", "")
        return bool(key and key.strip() and key != "your-gemini-api-key")

    def extract_attributes(self, text: str, category: str, expected_schema: Type[T]) -> T:
        self._ensure_configured()
        if not _GENAI_AVAILABLE or not self._has_api_key():
            return expected_schema()

        model = genai.GenerativeModel(
            self.model_name,
            system_instruction="You are an expert master data engineering attribute extractor."
        )
        prompt = f"Extract the technical attributes for a {category} from the following text:\n\n{text}"
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=expected_schema,
                temperature=0.0
            )
        )
        return expected_schema.model_validate_json(response.text)

    def classify(self, text: str, taxonomy: Dict[str, str]) -> str:
        self._ensure_configured()
        if not _GENAI_AVAILABLE or not self._has_api_key():
            return list(taxonomy.keys())[0] if taxonomy else "UNKNOWN"

        model = genai.GenerativeModel(
            self.model_name,
            system_instruction="You are a master data classifier. You only output exactly one ID."
        )
        prompt = (
            f"Classify the following material description into ONE of the provided taxonomy IDs.\n\n"
            f"Description: {text}\n\nTaxonomy Mapping: {json.dumps(taxonomy, indent=2)}\n\n"
            f"Respond ONLY with the EXACT taxonomy ID, nothing else."
        )
        response = model.generate_content(prompt, generation_config=genai.GenerationConfig(temperature=0.0))
        return response.text.strip()

    def generate_canonical_description(self, attributes: Dict[str, Any]) -> str:
        self._ensure_configured()
        if not _GENAI_AVAILABLE or not self._has_api_key():
            return "CANONICAL MATERIAL DESCRIPTION"

        model = genai.GenerativeModel(
            self.model_name,
            system_instruction="You output short, precise noun-modifier engineering descriptions in ALL CAPS."
        )
        prompt = f"Generate a canonical, normalized engineering short description (max 40 chars) from these attributes:\n{json.dumps(attributes)}"
        response = model.generate_content(prompt, generation_config=genai.GenerationConfig(temperature=0.1))
        return response.text.strip()

    def explain_match(self, context: Dict[str, Any]) -> str:
        self._ensure_configured()
        if not _GENAI_AVAILABLE or not self._has_api_key():
            return "Mock explanation: materials are similar based on attributes."

        model = genai.GenerativeModel(
            self.model_name,
            system_instruction="You are a strict data governance AI. You never hallucinate data."
        )
        prompt = (
            f"Based ONLY on the provided context, generate a 1 sentence explanation of the match decision. "
            f"DO NOT invent facts outside the context.\n\nContext:\n{json.dumps(context, indent=2)}"
        )
        response = model.generate_content(prompt, generation_config=genai.GenerationConfig(temperature=0.0))
        return response.text.strip()
