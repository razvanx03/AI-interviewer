# CV Schemas (`api/schemas/cv.py`)

Defines data validation schemas for in-memory batch extraction of candidate CV documents.

---

## 1. `ExtractedCandidateItem`
- `filename`: Uploaded file name.
- `file_type`: Document type (`pdf` or `docx`).
- `raw_text`: Sanitized plain text extracted from the document in-memory.
- `extracted_name`: Candidate full name inferred from document header or filename (optional).
- `file_size`: Integer size of the document in bytes.

---

## 2. `BatchExtractResponse`
Response schema returned by `POST /api/v1/cv/extract-batch`:
- `candidates`: List of `ExtractedCandidateItem` objects ready for UI display and RAG screening.
