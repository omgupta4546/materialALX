import uuid
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="")
correlation_id_ctx_var: ContextVar[str] = ContextVar("correlation_id", default="")

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        corr_id = request.headers.get("X-Correlation-ID", req_id)
        
        request_id_ctx_var.set(req_id)
        correlation_id_ctx_var.set(corr_id)
        
        response = await call_next(request)
        
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Correlation-ID"] = corr_id
        
        return response

def get_request_id() -> str:
    return request_id_ctx_var.get()

def get_correlation_id() -> str:
    return correlation_id_ctx_var.get()
