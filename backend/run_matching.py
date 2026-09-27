"""Trigger matching directly (bypassing API) for existing source materials."""
import logging, sys, threading, uuid
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(asctime)s %(levelname)s: %(message)s')

from app.core.connection import SessionLocal
from app.models.base import ProcessingJob, SourceMaterial, NormalizedMaterial

db = SessionLocal()

# Find unmatched source materials
all_sm = db.query(SourceMaterial).filter(SourceMaterial.source_file == 'mapped_upload.csv').all()
matched_ids = {n.source_material_id for n in db.query(NormalizedMaterial.source_material_id).all()}
unmatched = [sm for sm in all_sm if sm.source_material_id not in matched_ids]

cpse_id = all_sm[0].cpse_id if all_sm else None
print(f"Total: {len(all_sm)}, Already matched: {len(matched_ids)}, Unmatched: {len(unmatched)}")

if not unmatched:
    print("All materials already matched!")
    db.close()
    exit(0)

# Create job
job_id = f"MATCH-{uuid.uuid4().hex[:12]}"
job = ProcessingJob(
    job_id=job_id, job_type="AI_MATCHING", status="RUNNING",
    total_records=len(unmatched), records_processed=0, successful=0, failed=0,
    current_stage="AI_MATCHING", details={"cpse_id": cpse_id}
)
db.add(job)
db.commit()
print(f"Job created: {job_id}")

# Run matching synchronously (not in thread) so we can see progress
from app.ai.pipeline import MatchingPipeline

tdb = SessionLocal()
pipeline = MatchingPipeline(tdb)
tjob = tdb.query(ProcessingJob).filter_by(job_id=job_id).first()

for idx, sm in enumerate(unmatched):
    try:
        result = pipeline.process(sm.source_material_id)
        tjob.successful = (tjob.successful or 0) + 1
        status = f"matched={result}" if result else "no-match"
    except Exception as e:
        tjob.failed = (tjob.failed or 0) + 1
        status = f"error={e}"
    
    tjob.records_processed = idx + 1
    if idx % 10 == 0:
        tdb.commit()
        print(f"  [{idx+1}/{len(unmatched)}] {sm.legacy_material_code}: {status}")

tjob.records_processed = tjob.total_records
tjob.status = "COMPLETED"
tjob.current_stage = "FINISHED"
tdb.commit()

nm_count = tdb.query(NormalizedMaterial).count()
from app.models.base import MatchResult
mr_count = tdb.query(MatchResult).count()
print(f"\nDone! Normalized: {nm_count}, Matches: {mr_count}")
print(f"Job {job_id}: ok={tjob.successful} fail={tjob.failed}")
tdb.close()
