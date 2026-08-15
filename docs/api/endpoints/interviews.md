# API Endpoints (`api/endpoints/`)

## 1. `interviews.py`
- `POST /api/v1/interviews`: Creates a new interview session.
  - Body: `InterviewCreate`
  - Response: `InterviewResponse` (HTTP 201)
- `GET /api/v1/interviews/{interview_id}`: Retrieves session state.
  - Response: `InterviewResponse` (HTTP 200 or 404)
- `GET /api/v1/interviews/{interview_id}/messages`: Retrieves chat transcript.
  - Response: `List[ChatMessage]` (HTTP 200 or 404)

## 2. `chat.py`
- `POST /api/v1/interviews/{interview_id}/chat`: Sends candidate answer and gets next AI question.
  - Body: `ChatRequest` (`{ content: "..." }`)
  - Response: `ChatResponse`
- `WS /api/v1/interviews/{interview_id}/ws`: WebSocket connection for bidirectional streaming.
  - Receives `{ content: "..." }`
  - Sends streaming events: `stream_start`, `chunk`, `stream_end`.

## 3. `cv.py`
- `POST /api/v1/cv/upload`: Multipart file upload for PDF, DOCX, DOC, or TXT.
  - Response: `CVParseResult`
