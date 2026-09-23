from enum import Enum
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.ai.base import BaseAIModule

class MatchType(str, Enum):
    EXACT_DUPLICATE = "EXACT_DUPLICATE"
    NEAR_DUPLICATE = "NEAR_DUPLICATE"
    FUNCTIONALLY_EQUIVALENT = "FUNCTIONALLY_EQUIVALENT"
    RELATED = "RELATED"
    NOT_EQUIVALENT = "NOT_EQUIVALENT"
    REQUIRES_ENGINEERING_REVIEW = "REQUIRES_ENGINEERING_REVIEW"

class PairwiseMatcherConfig(BaseModel):
    weight_semantic: float = 0.3
    weight_attribute: float = 0.4
    weight_manufacturer: float = 0.1
    weight_mpn: float = 0.2
    
    penalty_missing_attribute: float = -0.05
    penalty_critical_conflict: float = -0.50

class PairwiseMatcherInput(BaseModel):
    source_attributes: Dict[str, Any]
    candidate_attributes: Dict[str, Any]
    
    source_manufacturer: Optional[str] = None
    candidate_manufacturer: Optional[str] = None
    
    source_mpn: Optional[str] = None
    candidate_mpn: Optional[str] = None
    
    source_category: Optional[str] = None
    candidate_category: Optional[str] = None
    
    # Caller should resolve the UOM dimension and pass it if applicable
    source_uom_dimension: Optional[str] = None
    candidate_uom_dimension: Optional[str] = None
    
    semantic_similarity: float
    rule_engine_veto: bool = False

class PairwiseMatcherOutput(BaseModel):
    semantic_score: float
    attribute_score: float
    rule_score: float
    final_score: float
    evidence: List[str]
    conflicts: List[str]
    attribute_matches: List[str]
    uom_compatibility: str
    match_type: MatchType
    version: str

class PairwiseMatcherModule(BaseAIModule[PairwiseMatcherInput, PairwiseMatcherOutput, PairwiseMatcherConfig]):
    @property
    def version(self) -> str:
        return "2.0.0"

    def get_default_config(self) -> PairwiseMatcherConfig:
        return PairwiseMatcherConfig()

    def process(self, input_data: PairwiseMatcherInput) -> PairwiseMatcherOutput:
        self.logger.info("Evaluating pairwise match")
        
        evidence = []
        conflicts = []
        attribute_matches = []
        
        # 1. Semantic Score (Directly passed)
        semantic_score = input_data.semantic_similarity
        if semantic_score > 0.90:
            evidence.append("High semantic similarity.")
            
        # 2. Attribute Score
        attr_score = 0.0
        keys = set(input_data.source_attributes.keys()).union(input_data.candidate_attributes.keys())
        
        if keys:
            match_count = 0
            for k in keys:
                s_val = str(input_data.source_attributes.get(k, "")).strip().lower()
                c_val = str(input_data.candidate_attributes.get(k, "")).strip().lower()
                
                if not s_val or not c_val:
                    # Missing attribute penalty
                    attr_score += self.config.penalty_missing_attribute
                    conflicts.append(f"Missing attribute: {k}")
                elif s_val == c_val:
                    match_count += 1
                    attribute_matches.append(f"{k}: '{s_val}'")
                else:
                    # Conflicting attribute
                    attr_score += self.config.penalty_critical_conflict
                    conflicts.append(f"Attribute conflict on {k}: '{s_val}' != '{c_val}'")
            
            # Base attribute score is % of exact matches, then apply penalties
            base_attr = match_count / len(keys)
            attr_score = max(0.0, base_attr + attr_score)
        else:
            attr_score = 1.0 # No attributes to compare, neutral
            
        if attr_score > 0.9:
            evidence.append("Strong attribute alignment.")
            
        # 3. Rule Score (MFG, MPN, Category, UOM)
        rule_score = 0.0
        rule_max = 0.0
        
        if input_data.source_manufacturer and input_data.candidate_manufacturer:
            rule_max += self.config.weight_manufacturer
            if input_data.source_manufacturer.lower() == input_data.candidate_manufacturer.lower():
                rule_score += self.config.weight_manufacturer
                evidence.append("Manufacturer match.")
            else:
                conflicts.append("Manufacturer mismatch.")
                rule_score += self.config.penalty_critical_conflict
                
        if input_data.source_mpn and input_data.candidate_mpn:
            rule_max += self.config.weight_mpn
            if input_data.source_mpn.lower() == input_data.candidate_mpn.lower():
                rule_score += self.config.weight_mpn
                evidence.append("MPN match.")
            else:
                conflicts.append("MPN mismatch.")
                rule_score += self.config.penalty_critical_conflict
                
        # UOM Clash logic
        uom_clash = False
        uom_compatibility = "MATCH (or NA)"
        if input_data.source_uom_dimension and input_data.candidate_uom_dimension:
            if input_data.source_uom_dimension != input_data.candidate_uom_dimension:
                conflicts.append(f"UOM Dimension Clash: {input_data.source_uom_dimension} vs {input_data.candidate_uom_dimension}")
                uom_clash = True
                uom_compatibility = "CLASH"
            else:
                uom_compatibility = f"MATCH ({input_data.source_uom_dimension})"
                
        if rule_max > 0:
            rule_score = max(0.0, rule_score / rule_max)
        else:
            rule_score = 1.0 # Neutral if no rules apply
            
        # 4. Final Score Calculation
        # Normalize weights so they sum to 1 if rules are missing
        w_sem = self.config.weight_semantic
        w_attr = self.config.weight_attribute
        w_rule = self.config.weight_manufacturer + self.config.weight_mpn
        
        total_w = w_sem + w_attr + w_rule
        
        final_score = (
            (semantic_score * w_sem) +
            (attr_score * w_attr) +
            (rule_score * w_rule)
        ) / total_w
        
        # 5. Mapping to MatchType
        match_type = MatchType.NOT_EQUIVALENT
        
        # Enforce Engineering Veto
        if input_data.rule_engine_veto:
            match_type = MatchType.NOT_EQUIVALENT
            final_score = min(final_score, 0.40)  # Clamp score severely
            conflicts.append("Engineering Veto: Critical attributes conflict (blocking functional equivalence).")
        elif uom_clash or len([c for c in conflicts if "conflict" in c.lower()]) >= 2:
            match_type = MatchType.REQUIRES_ENGINEERING_REVIEW
        elif final_score >= 0.95:
            match_type = MatchType.EXACT_DUPLICATE
        elif final_score >= 0.85:
            match_type = MatchType.NEAR_DUPLICATE
        elif final_score >= 0.65:
            match_type = MatchType.FUNCTIONALLY_EQUIVALENT
        elif final_score >= 0.50:
            match_type = MatchType.RELATED
            
        return PairwiseMatcherOutput(
            semantic_score=round(semantic_score, 4),
            attribute_score=round(attr_score, 4),
            rule_score=round(rule_score, 4),
            final_score=round(final_score, 4),
            evidence=evidence,
            conflicts=conflicts,
            attribute_matches=attribute_matches,
            uom_compatibility=uom_compatibility,
            match_type=match_type,
            version=self.version
        )
