# API Core Config (`api/core/config.py`)

## 1. Environment Settings
- `PROJECT_NAME`: `"AI Job Interviewer API"`
- `API_V1_STR`: `"/api/v1"`
- `ENVIRONMENT`: `"development"` | `"production"`
- `CORS_ORIGINS`: `["http://localhost:5173", "http://127.0.0.1:5173", "http://0.0.0.0:5173", "http://localhost:3000", "http://localhost:8000"]`
- `OLLAMA_BASE_URL`: `"http://localhost:11434"`
- `DEFAULT_LLM_MODEL`: `"hf.co/radi04/qwen3-8b-cs-interviewer-merge-v1-150-q4:Q4_K_M"`
- `DEFAULT_EMBEDDING_MODEL`: `"nomic-embed-text"`
- `LLM_PROVIDER`: `"ollama"` | `"mock"`
- `DATABASE_URL`: Async connection string (`postgresql+asyncpg://...`).
