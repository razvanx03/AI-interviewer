# CV Schemas (`api/schemas/cv.py`)

Defines data validation schemas for document upload, structured parsing results, and database responses.

---

## 1. `CVParseResult`
- `id`: Unique CV identifier (UUID prefix).
- `filename`: Uploaded file name.
- `file_type`: Document type (`pdf` or `docx`).
- `file_size_bytes`: Integer size in bytes.
- `storage_path`: Relative filesystem path.
- `extracted_text`: Raw plain text extracted from document.
- `parsed_data`: Structured JSON candidate metadata.
- `parsing_status`: Parsing status (`pending`, `completed`, `failed`).
- `created_at`: Datetime timestamp.

---

## 2. `CVResponse`
Full API response schema representing a persisted CV record in PostgreSQL:
- `id`, `user_id`, `interview_id`
- `file_name`, `file_type`, `file_size`, `storage_path`
- `raw_text`, `parsed_data`, `parsing_status`
- `created_at`, `updated_at`
