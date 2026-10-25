from enum import Enum
from typing import List, Optional, Set
from fastapi import Header, HTTPException, Depends, status
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    SCRUTINY_OFFICER = "SCRUTINY_OFFICER"
    CHIEF_INSPECTOR = "CHIEF_INSPECTOR"
    PUBLIC_VIEWER = "PUBLIC_VIEWER"


class Permission(str, Enum):
    VIEW_FINDINGS = "VIEW_FINDINGS"
    EXECUTE_EVALUATION = "EXECUTE_EVALUATION"
    UPLOAD_DOCUMENT = "UPLOAD_DOCUMENT"
    OFFICER_OVERRIDE = "OFFICER_OVERRIDE"
    CHIEF_SIGN_OFF = "CHIEF_SIGN_OFF"
    VERIFY_AUDIT_CHAIN = "VERIFY_AUDIT_CHAIN"


ROLE_PERMISSIONS: dict[UserRole, Set[Permission]] = {
    UserRole.SCRUTINY_OFFICER: {
        Permission.VIEW_FINDINGS,
        Permission.EXECUTE_EVALUATION,
        Permission.UPLOAD_DOCUMENT,
        Permission.OFFICER_OVERRIDE,
    },
    UserRole.CHIEF_INSPECTOR: {
        Permission.VIEW_FINDINGS,
        Permission.EXECUTE_EVALUATION,
        Permission.UPLOAD_DOCUMENT,
        Permission.OFFICER_OVERRIDE,
        Permission.CHIEF_SIGN_OFF,
        Permission.VERIFY_AUDIT_CHAIN,
    },
    UserRole.PUBLIC_VIEWER: {
        Permission.VIEW_FINDINGS,
    },
}


class UserSession(BaseModel):
    user_id: str
    role: UserRole
    badge_number: Optional[str] = None
    permissions: List[Permission] = Field(default_factory=list)


def get_current_user(
    x_api_role: Optional[str] = Header(None, alias="X-API-Role"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_badge_id: Optional[str] = Header(None, alias="X-Badge-ID"),
    authorization: Optional[str] = Header(None),
) -> UserSession:
    """
    Extracts authenticated user session and role from headers.
    Defaults to SCRUTINY_OFFICER in local non-header development mode,
    but strictly parses and validates explicit roles when provided.
    """
    raw_role = x_api_role
    if not raw_role and authorization:
        # Check bearer token role
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].upper()
            if token in UserRole.__members__:
                raw_role = token

    role_str = (raw_role or UserRole.SCRUTINY_OFFICER.value).upper()
    try:
        role = UserRole(role_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid user role: '{role_str}'. Valid roles: {[r.value for r in UserRole]}",
        )

    user_id = x_user_id or f"USER-{role.value}"
    badge_id = x_badge_id or "AICTE-OFFICER-001"
    permissions = list(ROLE_PERMISSIONS.get(role, set()))

    return UserSession(
        user_id=user_id,
        role=role,
        badge_number=badge_id,
        permissions=permissions,
    )


def require_permission(perm: Permission):
    """FastAPI dependency to enforce specific permission requirements."""
    def dependency(user: UserSession = Depends(get_current_user)) -> UserSession:
        if perm not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Role '{user.role.value}' lacks required permission '{perm.value}'.",
            )
        return user
    return dependency


def require_role(allowed_roles: List[UserRole]):
    """FastAPI dependency to restrict endpoints to specific roles."""
    def dependency(user: UserSession = Depends(get_current_user)) -> UserSession:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Role '{user.role.value}' is not authorized. Allowed: {[r.value for r in allowed_roles]}",
            )
        return user
    return dependency
