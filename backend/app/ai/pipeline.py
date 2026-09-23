import logging
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.base import SourceMaterial, NormalizedMaterial, NationalMaterial, MatchResult
from app.repositories.vector_repo import VectorRepository

# Import all AI modules
from app.ai.modules.normalizer import NormalizerModule, NormalizerInput
from app.ai.modules.attribute_extractor import AttributeExtractorModule, AttributeExtractorInput
from app.ai.modules.classifier import ClassifierModule, ClassifierInput
from app.ai.modules.embedding_generator import EmbeddingGeneratorModule, EmbeddingGeneratorInput, EmbeddingInputData
from app.ai.embedding.providers.local_sentence_transformers import LocalSentenceTransformerProvider
from app.ai.modules.candidate_retriever import CandidateRetrieverModule, CandidateRetrieverInput, RawVectorCandidate
from app.ai.modules.rule_engine import RuleEngineModule, RuleEngineInput
from app.ai.modules.pairwise_matcher import PairwiseMatcherModule, PairwiseMatcherInput, MatchType
from app.ai.modules.risk_engine import RiskEngineModule, RiskEngineInput
from app.ai.modules.explanation_generator import ExplanationGeneratorModule, ExplanationGeneratorInput

logger = logging.getLogger(__name__)

class MatchingPipeline:
    """
    Orchestrates the entire AI Matching Pipeline for a single SourceMaterial.
    Normalization -> UOM -> Attributes -> Classification -> Embedding -> Vector Search
    -> Pairwise Match -> Rule Engine -> Risk -> Save Match.
    """
    def __init__(self, db: Session):
        self.db = db
        self.vector_repo = VectorRepository(db)
        
        # Initialize modules
        self.normalizer = NormalizerModule()
        self.attribute_extractor = AttributeExtractorModule()
        self.classifier = ClassifierModule()
        
        # Hook up the actual embedding provider
        self.embedding_provider = LocalSentenceTransformerProvider()
        self.embedding_generator = EmbeddingGeneratorModule(provider=self.embedding_provider)
        
        self.candidate_retriever = CandidateRetrieverModule()
        self.rule_engine = RuleEngineModule()
        self.pairwise_matcher = PairwiseMatcherModule()
        self.risk_engine = RiskEngineModule()
        self.explanation_generator = ExplanationGeneratorModule()

    def process(self, source_material_id: str) -> Optional[str]:
        """
        Executes the matching pipeline and returns the primary created match_id (if any).
        """
        logger.info(f"Starting matching pipeline for {source_material_id}")
        
        # 1. Fetch SourceMaterial
        source = self.db.query(SourceMaterial).filter_by(source_material_id=source_material_id).first()
        if not source:
            logger.error(f"SourceMaterial {source_material_id} not found.")
            return None
            
        raw_text = f"{source.raw_description} {source.raw_category} {source.manufacturer}".strip()
        
        # 2. Normalization
        norm_out = self.normalizer.process(NormalizerInput(raw_text=source.raw_description or ""))
        
        # 3. Attribute Extraction
        attr_out = self.attribute_extractor.process(AttributeExtractorInput(
            raw_text=raw_text,
            normalized_text=norm_out.normalized_text
        ))
        
        # 4. Classification
        class_out = self.classifier.process(ClassifierInput(
            normalized_text=norm_out.normalized_text,
            attributes={attr.attribute: attr.value for attr in attr_out.attributes}
        ))
        
        # 5. Embedding
        embed_out = self.embedding_generator.process(EmbeddingGeneratorInput(
            items=[EmbeddingInputData(
                category=source.raw_category,
                normalized_description=norm_out.normalized_text,
                attributes={attr.attribute: str(attr.value) for attr in attr_out.attributes},
                manufacturer=source.manufacturer,
                manufacturer_part_number=source.manufacturer_part_number
            )]
        ))
        
        # 6. Retrieve Vector Candidates (pgvector)
        raw_candidates = self.vector_repo.get_top_k_candidates(embedding=embed_out.embeddings[0], k=10)
        
        # Convert to RawVectorCandidate for retriever
        parsed_candidates = []
        for rc in raw_candidates:
            parsed_candidates.append(RawVectorCandidate(
                national_material_id=rc["national_material_id"],
                similarity_score=rc["similarity_score"],
                category=rc["category"],
                status=rc["status"],
                metadata=rc["metadata"]
            ))
            
        retriever_out = self.candidate_retriever.process(CandidateRetrieverInput(
            raw_candidates=parsed_candidates,
            category_filter=class_out.classification_id
        ))
        
        best_match_id = None
        
        # Check if NormalizedMaterial exists for source; if not we should probably create one, 
        # but matching pipeline focuses on generating MatchResults. 
        norm_rec = self.db.query(NormalizedMaterial).filter_by(source_material_id=source_material_id).first()
        if not norm_rec:
            norm_rec = NormalizedMaterial(
                normalized_material_id=f"NORM-{uuid.uuid4().hex[:8]}",
                source_material_id=source_material_id,
                normalized_description=norm_out.normalized_text,
                category_code=class_out.classification_id,
                attributes={attr.attribute: str(attr.value) for attr in attr_out.attributes},
                embedding=embed_out.embeddings[0],
                confidence=class_out.confidence
            )
            self.db.add(norm_rec)
            self.db.flush()
        
        # 7. Evaluate Candidates
        for cand in retriever_out.candidates:
            nat_mat = self.db.query(NationalMaterial).filter_by(national_material_id=cand.candidate_id).first()
            if not nat_mat:
                continue
                
            # Rule Engine for critical attributes
            rule_out = self.rule_engine.process(RuleEngineInput(
                category=class_out.classification_id,
                source_attributes={attr.attribute: str(attr.value) for attr in attr_out.attributes},
                candidate_attributes=nat_mat.attributes or {}
            ))
            
            # Pairwise Match
            pm_out = self.pairwise_matcher.process(PairwiseMatcherInput(
                source_attributes={attr.attribute: str(attr.value) for attr in attr_out.attributes},
                candidate_attributes=nat_mat.attributes or {},
                source_manufacturer=source.manufacturer,
                candidate_manufacturer=nat_mat.attributes.get("manufacturer") if nat_mat.attributes else None,
                semantic_similarity=cand.similarity,
                rule_engine_veto=rule_out.blocks_functional_equivalence
            ))
            
            risk_out = self.risk_engine.process(RiskEngineInput(
                match_confidence=pm_out.final_score,
                category=class_out.classification_id,
                critical_conflicts=rule_out.critical_conflicts,
                missing_critical_fields=rule_out.missing_critical_fields
            ))
            
            # Generate Deterministic Explanation
            classification_comp = "MATCH" if class_out.classification_id == nat_mat.classification_id else "MISMATCH"
            
            exp_out = self.explanation_generator.process(ExplanationGeneratorInput(
                retrieval_reason="Retrieved via pgvector cosine similarity search (top-10).",
                semantic_similarity=pm_out.semantic_score,
                attribute_matches=pm_out.attribute_matches,
                attribute_conflicts=pm_out.conflicts,
                uom_compatibility=pm_out.uom_compatibility,
                classification_compatibility=classification_comp,
                critical_rule_results=rule_out.conflict_details,
                risk_level=risk_out.risk_level.value,
                final_confidence=pm_out.final_score,
                recommended_action=risk_out.recommended_action,
                rules_version=self.rule_engine.version,
                calibration_version=self.risk_engine.version
            ))
            
            # 8. Save Match Result
            match_id = f"MATCH-{uuid.uuid4().hex[:8]}"
            match_res = MatchResult(
                match_id=match_id,
                material_a_id=norm_rec.normalized_material_id,
                material_b_id=nat_mat.national_material_id,
                semantic_score=pm_out.semantic_score,
                attribute_score=pm_out.attribute_score,
                rule_score=pm_out.rule_score,
                final_score=pm_out.final_score,
                match_type=pm_out.match_type.value,
                # Store full deterministic explanation
                positive_evidence=exp_out.model_dump(),
                negative_evidence={},
                conflicts={},
                recommendation=risk_out.recommended_action,
                risk_level=risk_out.risk_level.value,
                requires_human_review=(risk_out.recommended_action != "ALLOW_AUTOMATION"),
                created_at=datetime.utcnow(),
                
                # Traceability Metadata
                model_version=exp_out.model_version,
                prompt_version=exp_out.prompt_version,
                rules_version=exp_out.rules_version
            )
            self.db.add(match_res)
            
            if not best_match_id or pm_out.final_score > 0.85:
                best_match_id = match_id
                
        self.db.commit()
        logger.info(f"Pipeline finished for {source_material_id}. Best match: {best_match_id}")
        return best_match_id
