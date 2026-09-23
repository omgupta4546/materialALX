from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.rate_limit import limiter
from app.auth.router import router as auth_router
from app.auth.rbac import require_role, Roles
from app.notifications.router import router as notifications_router
from app.api.endpoints.uploads import router as uploads_router
from app.api.endpoints.materials import router as materials_router
from app.api.endpoints.cpses import router as cpses_router

from app.api.endpoints.matches import router as matches_router
from app.api.endpoints.national_materials import router as national_materials_router
from app.api.endpoints.classifications import router as classifications_router
from app.api.endpoints.analytics import router as analytics_router
from app.api.endpoints.mappings import router as mappings_router
from app.api.endpoints.jobs import router as jobs_router
from app.api.endpoints.data_quality import router as data_quality_router
from app.api.endpoints.rule_management import router as rule_management_router
from app.api.endpoints.feedback import router as feedback_router
from app.api.endpoints.admin import router as admin_router
from app.api.endpoints.uoms import router as uoms_router
from app.api.endpoints.procurement import router as procurement_router
from app.api.endpoints.exports import router as exports_router
from app.api.endpoints.migration import router as migration_router
from app.middleware.request_context import RequestContextMiddleware
from app.core.logging import setup_logging
from app.core.errors import register_error_handlers
from app.core.connection import check_db_health, engine
from app.models.base import Base

setup_logging()

# Define global error schemas
from pydantic import BaseModel
class ErrorModel(BaseModel):
    detail: str

responses = {
    400: {"model": ErrorModel, "description": "Bad Request"},
    401: {"model": ErrorModel, "description": "Unauthorized"},
    403: {"model": ErrorModel, "description": "Forbidden"},
    404: {"model": ErrorModel, "description": "Not Found"},
    422: {"model": ErrorModel, "description": "Validation Error"},
    500: {"model": ErrorModel, "description": "Internal Server Error"}
}

import os
from contextlib import asynccontextmanager
from arq import create_pool
from arq.connections import RedisSettings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from app.core.config import settings

    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass

    app.state.redis_pool = None
    try:
        redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
        app.state.redis_pool = await create_pool(redis_settings)
    except Exception:
        app.state.redis_pool = None
    yield
    # Shutdown
    if app.state.redis_pool:
        await app.state.redis_pool.close()

app = FastAPI(
    title="National Material Intelligence Backend",
    description="Main platform backend API. Supports AI-driven material deduplication and taxonomy governance.",
    version="1.0.0",
    openapi_tags=[
        {"name": "auth", "description": "Authentication and authorization operations."},
        {"name": "national-materials", "description": "Governed catalog of standardized materials."},
        {"name": "materials", "description": "Source materials uploaded from disparate systems."},
        {"name": "matches", "description": "AI-generated match recommendations and manual reviews."},
        {"name": "mappings", "description": "Explicit linkages between source and national materials."},
        {"name": "jobs", "description": "Background processing jobs for uploads and batch operations."},
        {"name": "cpses", "description": "Central Public Sector Enterprises metadata."},
        {"name": "classifications", "description": "Hierarchical taxonomy tree."},
        {"name": "Rule Management", "description": "Admin: configure critical rules, weights, thresholds and approval policy."},
        {"name": "Feedback", "description": "Human reviewer feedback capture and model analytics."},
        {"name": "Admin", "description": "Governance: users, roles, CPSEs, synonyms, UOMs, rules, model/prompt registries, audit."}
    ],
    responses=responses,
    lifespan=lifespan,
)

app.add_middleware(RequestContextMiddleware)

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

import uuid

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174", "http://localhost:5175", "http://127.0.0.1:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

register_error_handlers(app)

# Common dependencies for specific roles
all_roles = [Roles.ADMIN, Roles.ENGINEER, Roles.DATA_STEWARD, Roles.AUDITOR, Roles.CPSE_USER]
write_roles = [Roles.ADMIN, Roles.ENGINEER, Roles.DATA_STEWARD]
admin_roles = [Roles.ADMIN]

app.include_router(auth_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1", dependencies=[Depends(require_role(all_roles))])
app.include_router(uploads_router, prefix="/api/v1/materials", dependencies=[Depends(require_role(write_roles))])
app.include_router(materials_router, prefix="/api/v1/materials", dependencies=[Depends(require_role(all_roles))])
app.include_router(cpses_router, prefix="/api/v1/cpses", dependencies=[Depends(require_role(all_roles))])
app.include_router(matches_router, prefix="/api/v1/matches", dependencies=[Depends(require_role(all_roles))])
app.include_router(national_materials_router, prefix="/api/v1/national-materials", dependencies=[Depends(require_role(all_roles))])
app.include_router(classifications_router, prefix="/api/v1/classifications", dependencies=[Depends(require_role(all_roles))])
app.include_router(analytics_router, prefix="/api/v1/analytics", dependencies=[Depends(require_role(all_roles))])
app.include_router(mappings_router, prefix="/api/v1/mappings", dependencies=[Depends(require_role(all_roles))])
app.include_router(jobs_router, prefix="/api/v1", dependencies=[Depends(require_role(all_roles))])
app.include_router(data_quality_router, prefix="/api/v1/data-quality", dependencies=[Depends(require_role(all_roles))])
# Rule Management is intentionally NOT wrapped in all_roles at router level;
# individual endpoints enforce ADMIN_ONLY vs READ_ROLES internally.
app.include_router(rule_management_router, prefix="/api/v1/rules")
app.include_router(feedback_router, prefix="/api/v1/feedback")
app.include_router(admin_router, prefix="/api/v1/admin")
app.include_router(uoms_router)
app.include_router(procurement_router, prefix="/api/v1/analytics/procurement", dependencies=[Depends(require_role(all_roles))])
app.include_router(exports_router, prefix="/api/v1/exports")
app.include_router(migration_router, prefix="/api/v1/migration", dependencies=[Depends(require_role(admin_roles))])


from fastapi.responses import RedirectResponse

@app.get("/", include_in_schema=False)
def root():
    """Root endpoint — redirects to interactive API documentation."""
    return RedirectResponse(url="/docs")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "main-backend"}

@app.get("/ready")
def readiness_check():
    db_status = check_db_health()

    if db_status["status"] != "ok":
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Service Unavailable: Database not ready")

    return {
        "status": "ready",
        "service": "main-backend",
        "database": db_status
    }

@app.get("/api", include_in_schema=False)
def api_info():
    """API info — lists available route groups and useful links."""
    return {
        "platform": "National Material Intelligence & Harmonization Platform",
        "version": "1.0.0",
        "status": "running",
        "docs": {
            "swagger_ui": "http://localhost:8000/docs",
            "redoc":       "http://localhost:8000/redoc",
            "openapi_json":"http://localhost:8000/openapi.json",
        },
        "health_endpoints": {
            "health": "http://localhost:8000/health",
            "ready":  "http://localhost:8000/ready",
        },
        "api_routes": {
            "auth":               "/api/v1/auth",
            "materials":          "/api/v1/materials",
            "national_materials": "/api/v1/national-materials",
            "matches":            "/api/v1/matches",
            "mappings":           "/api/v1/mappings",
            "cpses":              "/api/v1/cpses",
            "classifications":    "/api/v1/classifications",
            "analytics":          "/api/v1/analytics",
            "jobs":               "/api/v1/jobs",
            "data_quality":       "/api/v1/data-quality",
            "rules":              "/api/v1/rules",
            "feedback":           "/api/v1/feedback",
            "admin":              "/api/v1/admin",
            "exports":            "/api/v1/exports",
            "procurement":        "/api/v1/analytics/procurement",
            "migration":          "/api/v1/migration",
        }
    }
