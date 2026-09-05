from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Job Interviewer API"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # CORS Settings
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://0.0.0.0:5173",
        "http://localhost:3000",
        "http://localhost:8000",
    ]
    CORS_ORIGIN_REGEX: Optional[str] = None

    @field_validator("CORS_ORIGINS")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # Ollama & AI Model settings (Required from .env)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    DEFAULT_LLM_MODEL: str
    DEFAULT_EMBEDDING_MODEL: str
    LLM_PROVIDER: str = "ollama"
    OLLAMA_NUM_CTX: int = 8192
    SAFETY_MAX_QUESTIONS: int = 30

    # Database connection string (Required from .env - fails fast if missing)
    DATABASE_URL: str

    # Authentication & JWT (Required from .env - fails fast if missing)
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        case_sensitive=True,
        extra="ignore",
    )

settings = Settings()
