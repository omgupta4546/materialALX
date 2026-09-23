from typing import List, Callable, Dict, Any, Optional
from fastapi import Depends, HTTPException, status, Query
from app.auth.router import get_current_user

# Pre-defined roles based on standard personas
class Roles:
    ADMIN = "ADMIN"
    CPSE_USER = "CPSE_USER"
    DATA_STEWARD = "DATA_STEWARD"
    ENGINEER = "ENGINEER"
    AUDITOR = "AUDITOR"

def require_role(allowed_roles: List[str]) -> Callable:
    """
    Dependency generator that checks if the current user has one of the allowed roles.
    """
    def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = current_user.get("role")
        if not user_role or user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {', '.join(allowed_roles)}",
            )
        return current_user
    return role_checker

def enforce_cpse_tenant(
    cpse_code: Optional[str] = Query(None, description="Filter by CPSE code"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Optional[str]:
    """
    Dependency that enforces CPSE multi-tenant boundaries.
    - If user is ADMIN or DATA_STEWARD, they can query any CPSE (returns the requested cpse_code).
    - If user is CPSE_USER, ENGINEER, or AUDITOR, they can ONLY query their own CPSE.
      This overrides the requested cpse_code with their own, or raises 403 if they explicitly asked for another.
    """
    user_role = current_user.get("role")
    user_cpse = current_user.get("cpse")

    if user_role in [Roles.ADMIN, Roles.DATA_STEWARD]:
        return cpse_code

    if not user_cpse or user_cpse == "ALL":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not bound to a specific CPSE."
        )

    if cpse_code and cpse_code != user_cpse:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cross-tenant data access is forbidden. You are restricted to CPSE: {user_cpse}"
        )

    return user_cpse
