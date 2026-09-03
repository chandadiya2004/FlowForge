from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.jobs import router as jobs_router
from app.api.workflows import router as workflows_router
from app.core.config import settings
from app.core.deps import require_role
from app.models.user import User

app = FastAPI(
    title="FlowForge API",
    description="Distributed Job-Processing Platform API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(workflows_router, prefix="/workflows", tags=["Workflows"])
app.include_router(jobs_router)  # Provides /jobs and /workflows/{id}/jobs


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Basic health check endpoint returning service status."""
    return {"status": "ok"}


# ==============================================================================
# TEMPORARY ENDPOINT: Milestone 2 RBAC verification only.
# REMOVE once real admin routes are implemented in future milestones.
# ==============================================================================
@app.get("/admin-check", tags=["Admin (Temporary)"])
def admin_check(
    admin_user: User = Depends(require_role("admin")),
) -> dict[str, str]:
    """TEMPORARY endpoint protected by require_role('admin') for RBAC verification."""
    role_str = admin_user.role.value if hasattr(admin_user.role, "value") else str(admin_user.role)
    return {
        "status": "ok",
        "message": "Admin access granted",
        "user_id": str(admin_user.id),
        "email": admin_user.email,
        "role": role_str,
    }
