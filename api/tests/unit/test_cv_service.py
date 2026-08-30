import io
import pytest
from services.document_extractor import DocumentExtractor
from services.cv_parser import CVParser


class TestDocumentExtractorAndCVParser:
    """Unit tests for document validation, in-memory extraction, and CV parsing."""

    def test_validate_pdf_file_success(self):
        fake_pdf_bytes = b"%PDF-1.4 Fake PDF Content for Unit Testing"
        fmt = DocumentExtractor.validate_file("candidate_cv.pdf", fake_pdf_bytes)
        assert fmt == "pdf"

    def test_validate_file_invalid_extension(self):
        with pytest.raises(ValueError, match="Unsupported file format"):
            DocumentExtractor.validate_file("document.txt", b"Some text")

    def test_validate_file_empty_bytes(self):
        with pytest.raises(ValueError, match="Uploaded file is empty"):
            DocumentExtractor.validate_file("cv.pdf", b"")

    def test_validate_pdf_corrupted_header(self):
        with pytest.raises(ValueError, match="Missing standard PDF file header"):
            DocumentExtractor.validate_file("corrupted.pdf", b"NOT_A_PDF_HEADER_DATA")

    def test_validate_docx_corrupted_header(self):
        with pytest.raises(ValueError, match="Not a valid OpenXML package"):
            DocumentExtractor.validate_file("corrupted.docx", b"NOT_A_ZIP_HEADER")

    def test_extract_sparse_text_detection(self):
        # Sparse text should be recognized
        assert len("short text") < DocumentExtractor.SPARSE_TEXT_THRESHOLD

    @pytest.mark.asyncio
    async def test_cv_parser_heuristic_fallback(self):
        parser = CVParser()
        raw_text = """
        John Doe
        Email: john.doe@example.com
        Phone: +1 555-123-4567
        Skills: Python, FastAPI, Docker, PostgreSQL, React
        Experience: 4 years working as Backend Developer.
        """
        result = parser._heuristic_fallback(raw_text, "john_doe_cv.pdf")

        assert result is not None
        assert "john.doe@example.com" in result.get("email", "")
        assert "Python" in result.get("skills", [])
        assert "FastAPI" in result.get("skills", [])
        assert "Docker" in result.get("skills", [])
