# API Backend (`api/`) Architecture

## 1. Overview
The `api/` directory contains the FastAPI asynchronous REST and WebSocket server with PostgreSQL database persistence.

## 2. Directory Structure Mirror
- [`core/`](core/)
  - [`config.md`](core/config.md): Environment settings, CORS, PostgreSQL `DATABASE_URL`
- [`db/`](db/)
  - `session.py`: Async SQLAlchemy engine (`create_async_engine`), `async_sessionmaker`, and `get_db` dependency
  - `base.py`: DeclarativeBase
- [`models/`](models/)
  - `interview.py`: `Interview` table (id, job_title, company_name, job_description, experience_level, candidate_name, cv_filename, status, timestamps)
  - `message.py`: `Message` table (id, interview_id [Foreign Key], role, content, question_number, timestamps)
- [`endpoints/`](endpoints/)
  - [`interviews.md`](endpoints/interviews.md): `POST /api/v1/interviews`, `GET /api/v1/interviews`, `GET /api/v1/interviews/{id}`, `DELETE /api/v1/interviews/{id}`
  - [`chat.md`](endpoints/chat.md): `POST /api/v1/interviews/{id}/chat`, `WS /api/v1/interviews/{id}/ws`
  - [`cv.md`](endpoints/cv.md): `POST /api/v1/cv/upload`
- [`schemas/`](schemas/)
  - [`interview.md`](schemas/interview.md): `InterviewCreate`, `InterviewResponse`
  - [`chat.md`](schemas/chat.md): `ChatMessage`, `ChatRequest`, `ChatResponse`
  - [`cv.md`](schemas/cv.md): `CVParseResult`
- [`services/`](services/)
  - [`interview_service.md`](services/interview_service.md): Database session orchestrator with async SQLAlchemy queries

## 3. Running the Server
```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Interactive Swagger docs: `http://localhost:8000/docs`
