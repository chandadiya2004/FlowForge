import json
from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(BACKEND_DIR / ".env"),
            str(PROJECT_ROOT / ".env"),
            ".env",
            "../.env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/flowforge"
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET: str = "flowforge_default_secret_key_change_in_production"
    JWT_EXPIRE_MINUTES: int = 60
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000"]
    RETRY_BASE_DELAY_SECONDS: float = 10.0
    RETRY_MAX_DELAY_SECONDS: float = 300.0

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def resolve_sqlite_path(cls, v: str) -> str:
        if (
            isinstance(v, str)
            and v.startswith("sqlite:///")
            and not v.startswith("sqlite:////")
            and not v.startswith("sqlite:///:memory:")
        ):
            # Resolve relative SQLite paths against BACKEND_DIR
            rel_path = v.replace("sqlite:///", "")
            if rel_path.startswith("./"):
                rel_path = rel_path[2:]
            abs_path = (BACKEND_DIR / rel_path).resolve()
            return f"sqlite:///{abs_path.as_posix()}"
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    return json.loads(v_stripped)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


settings = Settings()
