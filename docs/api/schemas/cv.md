# CV Schemas (`api/schemas/cv.py`)

## 1. `CVParseResult`
- `filename`: Uploaded file name.
- `file_size_bytes`: Integer size in bytes.
- `content_type`: MIME type (e.g. `application/pdf`).
- `extracted_text`: Raw plain text extracted from document.
- `extracted_skills`: List of parsed technical skill strings.
- `extracted_experience_years`: Estimated years of experience.
- `summary`: High-level candidate summary.
