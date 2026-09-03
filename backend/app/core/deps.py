import uuid
from typing import Callable, Union
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate JWT access token, returning the current active user.
    
    Raises:
        HTTPException: 401 if credentials cannot be validated or user is inactive.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        token_type = payload.get("type")
        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type: access token required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id_raw: str = payload.get("sub")
        if user_id_raw is None:
            raise credentials_exception
        user_id = uuid.UUID(user_id_raw)
    except (ValueError, KeyError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user account",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_role(*roles: Union[str, UserRole]) -> Callable[..., User]:
    """Dependency factory that verifies the current user possesses one of the allowed roles.
    
    Usage:
        @app.get("/admin-only", dependencies=[Depends(require_role("admin"))])
        def admin_route(): ...
        
        # Or inject current user directly:
        @app.get("/admin-only")
        def admin_route(admin_user: User = Depends(require_role("admin"))): ...
    """
    allowed_roles = {r.value if isinstance(r, UserRole) else str(r) for r in roles}

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        current_role = (
            current_user.role.value
            if isinstance(current_user.role, UserRole)
            else str(current_user.role)
        )
        if current_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role: {', '.join(allowed_roles)}",
            )
        return current_user

    return role_checker
