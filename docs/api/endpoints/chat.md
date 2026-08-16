# Chat & Streaming Endpoints (`api/endpoints/chat.py`)

## 1. `POST /api/v1/interviews/{interview_id}/stream`
- **Purpose**: Real-time token-by-token Server-Sent Events (SSE) stream for interview chat.
- **Protocol**: Standard HTTP `POST` returning `text/event-stream`.
- **Request Body**: `ChatRequest` (`{ content: "Candidate answer..." }`)
- **Stream Format**:
  - `data: {"chunk": "word ", "is_complete": false}\n\n`
  - `data: {"chunk": "", "is_complete": true, "message_id": "...", "question_number": 2, "done": true}\n\n`
- **Database Persistence**: Candidate message is inserted upon request, and full AI response is committed to the PostgreSQL `messages` table upon completion of the stream.

## 2. `POST /api/v1/interviews/{interview_id}/chat`
- **Purpose**: Synchronous single-response chat endpoint.
- **Request Body**: `ChatRequest`
- **Response**: `ChatResponse`

## 3. `WS /api/v1/interviews/{interview_id}/ws`
- **Purpose**: Bidirectional WebSocket endpoint for future voice and real-time audio channels.
