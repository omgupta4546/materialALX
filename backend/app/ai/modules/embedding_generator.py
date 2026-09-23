from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Optional, Any
from app.ai.base import BaseAIModule
from app.ai.embedding.provider import EmbeddingProvider
from app.ai.embedding.providers.local_sentence_transformers import LocalSentenceTransformerProvider

class EmbeddingGeneratorConfig(BaseModel):
    model_name: str = "all-mpnet-base-v2"
    dimensions: int = 768

class EmbeddingInputData(BaseModel):
    category: Optional[str] = None
    normalized_description: str
    attributes: Dict[str, str] = Field(default_factory=dict)
    manufacturer: Optional[str] = None
    manufacturer_part_number: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def prevent_db_ids(cls, data: Any) -> Any:
        if isinstance(data, dict):
            def walk(value: Any):
                if isinstance(value, dict):
                    for k, v in value.items():
                        if k.endswith('_id') or k == 'id':
                            raise ValueError(f"Database IDs are not allowed in embedding input: {k}")
                        walk(v)
                elif isinstance(value, list):
                    for item in value:
                        walk(item)
            walk(data)
        return data

class EmbeddingGeneratorInput(BaseModel):
    items: List[EmbeddingInputData]

class EmbeddingGeneratorOutput(BaseModel):
    embeddings: List[List[float]]
    model_version: str
    model_name: str

class EmbeddingGeneratorModule(BaseAIModule[EmbeddingGeneratorInput, EmbeddingGeneratorOutput, EmbeddingGeneratorConfig]):
    
    def __init__(self, provider: Optional[EmbeddingProvider] = None):
        super().__init__()
        # Use default local provider if none is injected
        self.provider = provider or LocalSentenceTransformerProvider(model_name=self.config.model_name)
    
    @property
    def version(self) -> str:
        return "1.1.0"

    def get_default_config(self) -> EmbeddingGeneratorConfig:
        return EmbeddingGeneratorConfig()
        
    def _construct_embedding_text(self, item: EmbeddingInputData) -> str:
        parts = []
        if item.category:
            parts.append(f"Category: {item.category}")
            
        parts.append(f"Description: {item.normalized_description}")
        
        if item.attributes:
            attr_strs = [f"{k}: {v}" for k, v in item.attributes.items()]
            parts.append(f"Attributes: {', '.join(attr_strs)}")
            
        if item.manufacturer:
            parts.append(f"Manufacturer: {item.manufacturer}")
            
        if item.manufacturer_part_number:
            parts.append(f"MPN: {item.manufacturer_part_number}")
            
        return "\n".join(parts)

    def process(self, input_data: EmbeddingGeneratorInput) -> EmbeddingGeneratorOutput:
        self.logger.info(f"Generating embeddings for batch of size {len(input_data.items)}")
        
        texts = [self._construct_embedding_text(item) for item in input_data.items]
        
        if not texts:
            return EmbeddingGeneratorOutput(
                embeddings=[],
                model_version=self.version,
                model_name=self.config.model_name
            )
            
        embeddings = self.provider.generate_embeddings(texts)
        
        # Dimension validation
        expected_dim = self.config.dimensions
        for idx, emb in enumerate(embeddings):
            if len(emb) != expected_dim:
                raise ValueError(
                    f"Dimension mismatch for item {idx}. Expected {expected_dim} dimensions, "
                    f"but provider returned {len(emb)} dimensions."
                )
            
        return EmbeddingGeneratorOutput(
            embeddings=embeddings,
            model_version=self.version,
            model_name=self.config.model_name
        )
