from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.ai.base import BaseAIModule

class CandidateRetrieverConfig(BaseModel):
    max_candidates: int = 10
    similarity_threshold: float = 0.6
    exclude_statuses: List[str] = ["REJECTED", "RETIRED"]

class RawVectorCandidate(BaseModel):
    national_material_id: str
    similarity_score: float
    category: Optional[str]
    status: str
    metadata: Dict[str, Any]

class CandidateRetrieverInput(BaseModel):
    raw_candidates: List[RawVectorCandidate]
    category_filter: Optional[str] = None
    status_filter: Optional[str] = None

class RetrievedCandidate(BaseModel):
    candidate_id: str
    similarity: float
    metadata: Dict[str, Any]

class CandidateRetrieverOutput(BaseModel):
    candidates: List[RetrievedCandidate]
    version: str

class CandidateRetrieverModule(BaseAIModule[CandidateRetrieverInput, CandidateRetrieverOutput, CandidateRetrieverConfig]):
    @property
    def version(self) -> str:
        return "2.0.0"

    def get_default_config(self) -> CandidateRetrieverConfig:
        return CandidateRetrieverConfig()

    def process(self, input_data: CandidateRetrieverInput) -> CandidateRetrieverOutput:
        self.logger.info(f"Filtering {len(input_data.raw_candidates)} raw vector candidates")
        
        filtered = []
        for raw in input_data.raw_candidates:
            # 1. Similarity Threshold
            if raw.similarity_score < self.config.similarity_threshold:
                continue
                
            # 2. Hard Status Exclusions (e.g. drop REJECTED/RETIRED instantly)
            if raw.status.upper() in [s.upper() for s in self.config.exclude_statuses]:
                continue
                
            # 3. Explicit Status Filter
            if input_data.status_filter and raw.status.upper() != input_data.status_filter.upper():
                continue
                
            # 4. Explicit Category Filter
            if input_data.category_filter and raw.category:
                if input_data.category_filter.upper() != raw.category.upper():
                    continue
                    
            filtered.append(RetrievedCandidate(
                candidate_id=raw.national_material_id,
                similarity=raw.similarity_score,
                metadata=raw.metadata
            ))
            
        # Ensure we only return up to max_candidates
        # We sort by similarity descending just in case the DB didn't, but pgvector should have.
        filtered.sort(key=lambda x: x.similarity, reverse=True)
        final_candidates = filtered[:self.config.max_candidates]
        
        return CandidateRetrieverOutput(
            candidates=final_candidates,
            version=self.version
        )
