import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from typing import List

from models.user import User
from core.deps import get_current_admin
from schemas.cv import BatchExtractResponse, ExtractedCandidateItem
from services.document_extractor import document_extractor
from services.interview_service import interview_service

logger = logging.getLogger("api.endpoints.cv")

MAX_CV_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_BATCH_FILES = 50

router = APIRouter()

@router.post("/extract-batch", response_model=BatchExtractResponse)
async def extract_batch_cv_documents(
    files: List[UploadFile] = File(...),
    admin: User = Depends(get_current_admin),
):
    """
    Extract real raw text and candidate names in-memory from multiple uploaded CV documents.
    Does not persist files permanently until an interview session is created.
    """
    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch exceeds maximum limit of {MAX_BATCH_FILES} files per request.",
        )

    extracted_items = []
    for file in files:
        filename = file.filename or "resume.pdf"
        file_bytes = await file.read()

        if len(file_bytes) > MAX_CV_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File '{filename}' exceeds maximum allowed size of 10MB.",
            )
        raw_text = ""
        file_type = "pdf" if filename.lower().endswith(".pdf") else "docx"

        try:
            raw_text, file_type = document_extractor.extract_text(filename, file_bytes)
        except ValueError as exc:
            logger.warning("Document extraction failed for %s: %s", filename, exc)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to extract readable text from '{filename}': {exc}",
            )
        except Exception as exc:
            logger.error("Unexpected error during document extraction for %s: %s", filename, exc, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal error processing document '{filename}': {exc}",
            )

        raw_text = raw_text.replace("\x00", "")
        extracted_name = None
        if raw_text and raw_text.strip():
            extracted_name = interview_service._extract_candidate_name_from_cv_text(raw_text)

        extracted_items.append(
            ExtractedCandidateItem(
                filename=filename,
                file_type=file_type,
                raw_text=raw_text,
                extracted_name=extracted_name,
                file_size=len(file_bytes),
            )
        )

    return BatchExtractResponse(candidates=extracted_items)
