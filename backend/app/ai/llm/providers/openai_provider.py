import json
import os
from typing import Dict, Any, Type, TypeVar
from pydantic import BaseModel

# openai is optional — not required in CI/test environments
try:
    import openai as _openai_module
    _OPENAI_AVAILABLE = True
except ImportError:
    _openai_module = None
    _OPENAI_AVAILABLE = False

from app.ai.llm.provider import LLMProvider

T = TypeVar('T', bound=BaseModel)


class OpenAIProvider(LLMProvider):
    """
    OpenAI implementation utilizing Structured Outputs for strict JSON adherence.
    Requires OPENAI_API_KEY environment variable.
    Falls back to mock behaviour when openai package is not installed.
    """

    def __init__(self):
        self.client = None
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def _get_client(self):
        if not self.client:
            if not _OPENAI_AVAILABLE:
                raise RuntimeError(
                    "openai package is not installed. "
                    "Install it with: pip install openai"
                )
            self.client = _openai_module.OpenAI()
        return self.client

    def extract_attributes(self, text: str, category: str, expected_schema: Type[T]) -> T:
        prompt = f"Extract the technical attributes for a {category} from the following text:\n\n{text}"
        response = self._get_client().beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert master data engineering attribute extractor."},
                {"role": "user", "content": prompt}
            ],
            response_format=expected_schema
        )
        return response.choices[0].message.parsed

    def classify(self, text: str, taxonomy: Dict[str, str]) -> str:
        prompt = (
            f"Classify the following material description into ONE of the provided taxonomy IDs.\n\n"
            f"Description: {text}\n\nTaxonomy Mapping: {json.dumps(taxonomy, indent=2)}\n\n"
            f"Respond ONLY with the EXACT taxonomy ID, nothing else."
        )
        response = self._get_client().chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a master data classifier. You only output exactly one ID."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        return response.choices[0].message.content.strip()

    def generate_canonical_description(self, attributes: Dict[str, Any]) -> str:
        prompt = f"Generate a canonical, normalized engineering short description (max 40 chars) from these attributes:\n{json.dumps(attributes)}"
        response = self._get_client().chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You output short, precise noun-modifier engineering descriptions in ALL CAPS."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        return response.choices[0].message.content.strip()

    def explain_match(self, context: Dict[str, Any]) -> str:
        prompt = (
            f"Based ONLY on the provided context, generate a 1 sentence explanation of the match decision. "
            f"DO NOT invent facts outside the context.\n\nContext:\n{json.dumps(context, indent=2)}"
        )
        response = self._get_client().chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a strict data governance AI. You never hallucinate data."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        return response.choices[0].message.content.strip()
