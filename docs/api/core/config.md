# API Core Config (`api/core/config.py`)

## 1. Environment Settings
- `PROJECT_NAME`: `"AI Job Interviewer API"`
- `API_V1_STR`: `"/api/v1"`
- `ENVIRONMENT`: `"development"` | `"production"`
- `CORS_ORIGINS`: Allowed origins list or comma-separated string from `.env`.
- `OLLAMA_BASE_URL`: `"http://localhost:11434"`
- `DEFAULT_LLM_MODEL`: `"hf.co/radi04/qwen3-8b-cs-interviewer-merge-v1-150-q4:Q4_K_M"`
- `DEFAULT_EMBEDDING_MODEL`: `"nomic-embed-text"`
- `LLM_PROVIDER`: `"ollama"` | `"mock"`
- `DATABASE_URL`: Async connection string (`postgresql+asyncpg://...`). Mandatory from `.env`.
- `JWT_SECRET_KEY`: Signed secret for admin JWT tokens. Mandatory from `.env` (fails fast on startup if missing).
- `JWT_ALGORITHM`: `"HS256"`
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token lifetime in minutes (default 10080 = 7 days).
