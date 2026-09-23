from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

# This is a stub for the VectorRepository which handles PostgreSQL pgvector HNSW querying.
class VectorRepository:
    def __init__(self, db: Session):
        self.db = db
        
    def get_top_k_candidates(self, embedding: List[float], k: int = 10) -> List[Dict[str, Any]]:
        """
        Executes a highly efficient pgvector '<=>' (cosine distance) query.
        This hits the HNSW index in PostgreSQL to avoid O(N^2) scans.
        
        Returns raw candidate dictionaries ready to be mapped into RawVectorCandidate schemas.
        """
        
        if self.db.bind.dialect.name == "sqlite":
            stmt = text("""
                SELECT 
                    nat.national_material_id, 
                    nat.classification_id as category, 
                    nat.status as status, 
                    1.0 as similarity_score,
                    nat.canonical_description as name
                FROM normalized_material nm
                JOIN material_mapping mm ON mm.source_material_id = nm.source_material_id
                JOIN national_material nat ON nat.national_material_id = mm.national_material_id
                WHERE nm.embedding IS NOT NULL
                LIMIT :k
            """)
            rows = self.db.execute(stmt, {"k": k}).fetchall()
        else:
            stmt = text("""
                SELECT 
                    nat.national_material_id, 
                    nat.classification_id as category, 
                    nat.status as status, 
                    1 - (nm.embedding <=> :vector) as similarity_score,
                    nat.canonical_description as name
                FROM normalized_material nm
                JOIN material_mapping mm ON mm.source_material_id = nm.source_material_id
                JOIN national_material nat ON nat.national_material_id = mm.national_material_id
                WHERE nm.embedding IS NOT NULL
                ORDER BY nm.embedding <=> :vector
                LIMIT :k
            """)
            
            # Ensure we pass the vector formatted properly for pgvector, e.g. '[0.1, 0.2, ...]'
            vector_str = "[" + ",".join(str(float(x)) for x in embedding) + "]"
            rows = self.db.execute(stmt, {"vector": vector_str, "k": k}).fetchall()
        
        results = []
        for row in rows:
            results.append({
                "national_material_id": row.national_material_id,
                "similarity_score": float(row.similarity_score),
                "category": row.category,
                "status": row.status,
                "metadata": {"name": row.name}
            })
            
        return results
