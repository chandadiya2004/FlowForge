from app.api.auth import router as auth_router
from app.api.dead_letters import router as dead_letters_router
from app.api.jobs import router as jobs_router
from app.api.system import router as system_router
from app.api.workflows import router as workflows_router

__all__ = [
    "auth_router",
    "dead_letters_router",
    "jobs_router",
    "system_router",
    "workflows_router",
]
