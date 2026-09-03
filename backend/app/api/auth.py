import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User, UserRole
from app.schemas.auth import (
    RefreshTokenRequest,
    Token,
    UserCreate,
    UserLogin,
    UserRead,
)

router = APIRouter()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db),
) -> User:
    """Register a new user. Defaults role to 'member'. Rejects duplicate email with 409."""
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email address already exists.",
        )

    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=UserRole.MEMBER,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post(
    "/login",
    response_model=Token,
    summary="User login with email and password",
)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db),
) -> Token:
    """Authenticate credentials and return JWT access and refresh tokens."""
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user account",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role_str = user.role.value if isinstance(user.role, UserRole) else str(user.role)
    token_data = {"sub": str(user.id), "role": role_str}

    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token using refresh token",
)
def refresh(
    body: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> Token:
    """Exchange a valid refresh token for a newly issued access token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type: refresh token required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id_raw = payload.get("sub")
        if not user_id_raw:
            raise credentials_exception
        user_id = uuid.UUID(user_id_raw)
    except (ValueError, KeyError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise credentials_exception

    role_str = user.role.value if isinstance(user.role, UserRole) else str(user.role)
    new_access_token = create_access_token(data={"sub": str(user.id), "role": role_str})

    return Token(
        access_token=new_access_token,
        refresh_token=body.refresh_token,
        token_type="bearer",
    )


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get current user profile",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> User:
    """Retrieve details for the currently authenticated user."""
    return current_user
