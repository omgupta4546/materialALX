import json
import os
from typing import Dict, Any, Type, TypeVar
from pydantic import BaseModel
import openai
from app.ai.llm.provider import LLMProvider

T = TypeVar('T', bound=BaseModel)

class OpenAIProvider(LLMProvider):
    """
    OpenAI implementation utilizing Structured Outputs for strict JSON adherence.
    Requires OPENAI_API_KEY environment variable.
    """
    
    def __init__(self):
        # We allow client instantiation to fail lazily if key is missing, 
        # so importing the module doesn't crash the app if using Mock
        self.client = None
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
    def _get_client(self):
        if not self.client:
            self.client = openai.OpenAI()
        return self.client
    
    def extract_attributes(self, text: str, category: str, expected_schema: Type[T]) -> T:
        prompt = f"Extract the technical attributes for a {category} from the following text:\n\n{text}"
        
        # Use Structured Outputs (response_format) to guarantee schema compliance
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
        prompt = f"Classify the following material description into ONE of the provided taxonomy IDs.\n\nDescription: {text}\n\nTaxonomy Mapping: {json.dumps(taxonomy, indent=2)}\n\nRespond ONLY with the EXACT taxonomy ID, nothing else."
        
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
        prompt = f"Based ONLY on the provided context, generate a 1 sentence explanation of the match decision. DO NOT invent facts outside the context.\n\nContext:\n{json.dumps(context, indent=2)}"
        
        response = self._get_client().chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a strict data governance AI. You never hallucinate data."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        
        return response.choices[0].message.content.strip()
