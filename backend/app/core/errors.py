import logging
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

log = logging.getLogger(__name__)

class DomainError(Exception):
    """Base exception for all domain/business logic errors."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

def register_error_handlers(app: FastAPI):
    
    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError):
        log.warning(f"DomainError: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": "about:blank",
                "title": "Domain Error",
                "status": exc.status_code,
                "detail": exc.message
            }
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        log.warning(f"ValueError: {str(exc)}")
        return JSONResponse(
            status_code=400,
            content={
                "type": "about:blank",
                "title": "Bad Request",
                "status": 400,
                "detail": str(exc)
            }
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
        log.error(f"Database error: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={
                "type": "about:blank",
                "title": "Database Error",
                "status": 500,
                "detail": "An internal database error occurred."
            }
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        log.error(f"Unhandled Exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "type": "about:blank",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "An unexpected internal server error occurred."
            }
        )
