# Document Extractor (`api/services/document_extractor.py`)

Independent document processing engine for PDF and DOCX documents with binary magic-byte validation and in-memory PaddleOCR fallback.

---

## 1. Magic Bytes & MIME Validation
- **PDF**: Enforces `%PDF-` binary signature.
- **DOCX**: Enforces `PK\x03\x04` ZIP container header and strictly verifies complete OpenXML internal structure (both `[Content_Types].xml` and `word/document.xml`).
- **File Size**: Enforces maximum upload limit of 10 MB per file (`MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024`). Rejects oversized files with HTTP 413.
- Rejects non-PDF/non-DOCX files, corrupt archives, and empty files with HTTP 400/413/422.

---

## 2. In-Memory Extraction & OCR Architecture

### PDF Processing (`extract_pdf`)
1. Uses `pypdf` to extract text page-by-page.
2. If a page has sparse or missing text (< 50 chars, e.g. scanned document), `pypdfium2` renders that specific page in-memory as a `PIL.Image` / `numpy.ndarray`.
3. Runs `PaddleOCR` on the rendered image and combines the extracted text.

### DOCX Processing (`extract_docx`)
1. Uses `python-docx` to extract text from all paragraphs and table cells.
2. If text is sparse (< 50 chars), inspects the ZIP package in-memory (`word/media/`), extracts embedded images, and runs `PaddleOCR`.
3. Merges normal and OCR text.

---

## 3. Zero Temporary Disk Writes
All extraction, PDF rendering, and OCR processing operate entirely in RAM (`io.BytesIO`), preserving privacy and performance.
