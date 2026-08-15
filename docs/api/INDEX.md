# API Backend (`api/`) Architecture

## 1. Overview
The `api/` directory contains the FastAPI asynchronous REST and WebSocket server with clean top-level folders.

## 2. Directory Structure Mirror
- [`core/`](core/)
  - [`config.md`](core/config.md): Environment settings, CORS, model endpoints
- [`endpoints/`](endpoints/)
  - [`interviews.md`](endpoints/interviews.md): `POST /api/v1/interviews`, `GET /api/v1/interviews/{id}`
  - [`chat.md`](endpoints/chat.md): `POST /api/v1/interviews/{id}/chat`, `WS /api/v1/interviews/{id}/ws`
  - [`cv.md`](endpoints/cv.md): `POST /api/v1/cv/upload`
- [`schemas/`](schemas/)
  - [`interview.md`](schemas/interview.md): `InterviewCreate`, `InterviewResponse`
  - [`chat.md`](schemas/chat.md): `ChatMessage`, `ChatRequest`, `ChatResponse`
  - [`cv.md`](schemas/cv.md): `CVParseResult`
- [`services/`](services/)
  - [`interview_service.md`](services/interview_service.md): Session orchestrator
  - [`cv_service.md`](services/cv_service.md): Resume parsing interface (PDF/DOCX)

## 3. Running the Server
```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Interactive Swagger docs: `http://localhost:8000/docs`
