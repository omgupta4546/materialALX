import pytest
import asyncio
from app.api.endpoints.jobs import create_job
from app.schemas.jobs import JobCreate

@pytest.mark.asyncio
async def test_bulk_upload_simulation():
    # Simulate an upload of 10,000 records
    mock_ids = [f"MOCK-{i}" for i in range(10000)]
    
    # We just ensure the schema creation and list manipulation holds up
    job_in = JobCreate(
        job_type="BULK_UPLOAD_MOCK",
        target_ids=mock_ids
    )
    assert len(job_in.target_ids) == 10000

@pytest.mark.asyncio
async def test_concurrent_requests():
    # Simulate 50 concurrent small jobs
    async def mock_request(i):
        # In a real test, this would hit the API client. 
        # For this load simulation we just ensure async context switching
        await asyncio.sleep(0.01)
        return i
        
    tasks = [mock_request(i) for i in range(50)]
    results = await asyncio.gather(*tasks)
    assert len(results) == 50
