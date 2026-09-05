# Chat & CV Schemas (`api/schemas/`)

## 1. `chat.py`
- `MessageRole`: Enum (`system`, `assistant`, `user`)
- `ChatMessage`: `{ id: str, role: MessageRole, content: str, created_at: datetime, feedback: Optional[str], question_number: Optional[int] }`
- `ChatRequest`: `{ content: str (min_length=1, max_length=5000) }`
- `ChatResponse`: `{ message: ChatMessage, is_complete: bool, next_question_number: Optional[int] }`

## 2. `cv.py`
- `CVParseResult`: `{ filename, file_size_bytes, content_type, extracted_text, extracted_skills, extracted_experience_years, summary }`
