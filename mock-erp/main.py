from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.responses import JSONResponse
import pandas as pd
import datetime
from typing import Optional
from models import HealthResponse, PaginatedResponse, MaterialResponse, SyncRequest, SyncResponse
import os

app = FastAPI(title="MOCK ERP API", description="DO NOT USE IN PRODUCTION. Simulated ERP endpoints for CPSE integration testing.")

# Allowed CPSEs
VALID_CPSES = {"NEC", "BUS", "CPI", "GME", "AHM"}

# In-memory data store
DATA_STORE = {}

@app.on_event("startup")
def load_data():
    global DATA_STORE
    csv_path = 'data/synthetic/source_materials.csv'
    
    if os.path.exists(csv_path):
        # We assume the API runs from the root directory
        df = pd.read_csv(csv_path, dtype=str)
        # Group by CPSE
        for cpse in VALID_CPSES:
            DATA_STORE[cpse] = df[df['cpse_code'] == cpse].to_dict('records')
        print(f"Loaded {len(df)} materials into Mock ERP memory from synthetic data.")
    else:
        print(f"WARNING: {csv_path} not found. Trying demo dataset...")
        csv_path = 'data/demo/demo_materials.csv'
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path, dtype=str)
            for cpse in VALID_CPSES:
                DATA_STORE[cpse] = df[df['cpse_code'] == cpse].to_dict('records')
            print(f"Loaded {len(df)} materials from demo dataset.")
        else:
            print("WARNING: No material CSV found. Mock ERP is empty.")
            for cpse in VALID_CPSES:
                DATA_STORE[cpse] = []

def get_tenant_data(cpse: str):
    if cpse not in VALID_CPSES:
        raise HTTPException(status_code=404, detail=f"CPSE {cpse} not found or not supported by this mock ERP.")
    return DATA_STORE.get(cpse, [])

def map_to_response(row: dict) -> dict:
    base_keys = {'cpse_code', 'material_code', 'description', 'uom', 'category', 'subcategory', 'manufacturer', 'manufacturer_part_number', 'procurement_id', 'plant', 'quantity', 'unit_price', 'total_spend', 'supplier', 'procurement_date'}
    
    attrs = {k: v for k, v in row.items() if k not in base_keys and pd.notna(v) and str(v).strip() != '' and str(v) != 'nan'}
    
    return {
        "cpse_code": str(row.get('cpse_code', '')),
        "material_code": str(row.get('material_code', '')),
        "description": str(row.get('description', '')),
        "uom": str(row.get('uom', '')),
        "category": str(row.get('category', '')),
        "subcategory": str(row.get('subcategory', '')),
        "manufacturer": str(row.get('manufacturer', '')),
        "manufacturer_part_number": str(row.get('manufacturer_part_number', '')),
        "attributes": attrs
    }

@app.get("/mock-erp/{cpse}/health", response_model=HealthResponse)
def health_check(cpse: str = Path(..., title="The CPSE Code")):
    if cpse not in VALID_CPSES:
        raise HTTPException(status_code=404, detail="Unknown CPSE")
    return HealthResponse(
        status="UP",
        message=f"Connected to simulated {cpse} ERP.",
        warning="MOCK ERP ONLY. NO SAP INTEGRATION.",
        cpse_code=cpse
    )

@app.get("/mock-erp/{cpse}/materials", response_model=PaginatedResponse)
def get_materials(
    cpse: str, 
    page: int = Query(1, ge=1), 
    limit: int = Query(50, ge=1, le=1000),
    updated_since: Optional[str] = None
):
    data = get_tenant_data(cpse)
    total = len(data)
    start = (page - 1) * limit
    end = start + limit
    
    chunk = data[start:end]
    results = [map_to_response(row) for row in chunk]
    
    return PaginatedResponse(
        total=total,
        page=page,
        limit=limit,
        data=results
    )

@app.get("/mock-erp/{cpse}/materials/search", response_model=PaginatedResponse)
def search_materials(
    cpse: str, 
    q: str,
    page: int = Query(1, ge=1), 
    limit: int = Query(50, ge=1, le=1000)
):
    data = get_tenant_data(cpse)
    query = q.lower()
    
    filtered = [
        row for row in data 
        if query in str(row.get('description', '')).lower() 
        or query in str(row.get('manufacturer_part_number', '')).lower()
        or query in str(row.get('material_code', '')).lower()
    ]
    
    total = len(filtered)
    start = (page - 1) * limit
    end = start + limit
    
    chunk = filtered[start:end]
    results = [map_to_response(row) for row in chunk]
    
    return PaginatedResponse(
        total=total,
        page=page,
        limit=limit,
        data=results
    )

@app.get("/mock-erp/{cpse}/materials/{material_code}", response_model=MaterialResponse)
def get_material(cpse: str, material_code: str):
    data = get_tenant_data(cpse)
    for row in data:
        if str(row.get('material_code')) == material_code:
            return map_to_response(row)
            
    raise HTTPException(status_code=404, detail="Material not found in this CPSE")

@app.get("/mock-erp/{cpse}/last-updated")
def get_last_updated(cpse: str):
    if cpse not in VALID_CPSES:
        raise HTTPException(status_code=404, detail="Unknown CPSE")
    return {"cpse_code": cpse, "last_updated_at": datetime.datetime.now().isoformat()}

@app.post("/mock-erp/{cpse}/sync", response_model=SyncResponse)
def sync_materials(cpse: str, request: SyncRequest):
    if cpse not in VALID_CPSES:
        raise HTTPException(status_code=404, detail="Unknown CPSE")
    return SyncResponse(
        status="SUCCESS",
        received_count=len(request.materials),
        message=f"[MOCK] Synchronized payload for {cpse}."
    )
