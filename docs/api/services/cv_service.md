# CV Service (`api/services/cv_service.py`)

The orchestration service managing candidate CV ingestion, storage, extraction, parsing, and database persistence.

---

## Key Functions

### `process_and_store_cv`
- **Inputs**: `db: AsyncSession`, `filename: str`, `file_bytes: bytes`, `user_id: Optional[str]`, `interview_id: Optional[str]`.
- **Workflow**:
  1. Validates magic bytes via `DocumentExtractor`.
  2. Extracts raw text in-memory with automatic PaddleOCR fallback.
  3. Uses `CVParser` to extract structured candidate details via Qwen LLM.
  4. Saves original document file to disk at `storage/cvs/<cv_id>.<ext>`.
  5. Records full metadata and structured data in PostgreSQL `cvs` table.
- **Returns**: `CV` database model.

### `get_cv` & `list_cvs`
- Queries stored CV records from PostgreSQL.

### `get_absolute_file_path`
- Resolves the filesystem path for original document download and retrieval.

### `delete_cv`
- Cascades deletion of the database record and removes the physical document from storage.
