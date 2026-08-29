import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from fastapi.responses import FileResponse
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models.user import User
from core.deps import get_current_admin
from schemas.cv import CVResponse
from services.cv_service import cv_service
from services.document_extractor import document_extractor
from services.interview_service import interview_service

logger = logging.getLogger("api.endpoints.cv")

router = APIRouter()

@router.post("/extract-batch")
async def extract_batch_cv_documents(
    files: List[UploadFile] = File(...),
    admin: User = Depends(get_current_admin),
):
    """
    Extract real raw text and candidate names in-memory from multiple uploaded CV documents.
    Does not persist files permanently until an interview session is created.
    """
    extracted_items = []
    for file in files:
        filename = file.filename or "resume.pdf"
        file_bytes = await file.read()
        raw_text = ""
        file_type = "pdf" if filename.lower().endswith(".pdf") else "docx"

        try:
            raw_text, file_type = document_extractor.extract_text(filename, file_bytes)
        except Exception as exc:
            logger.warning("Document extraction failed for %s: %s", filename, exc)
            try:
                raw_text = file_bytes.decode("utf-8", errors="ignore")
            except Exception:
                raw_text = ""

        extracted_name = None
        if raw_text and raw_text.strip():
            extracted_name = interview_service._extract_candidate_name_from_cv_text(raw_text)

        extracted_items.append({
            "filename": filename,
            "file_type": file_type,
            "raw_text": raw_text,
            "extracted_name": extracted_name,
            "file_size": len(file_bytes),
        })

    return {"candidates": extracted_items}

@router.post("/upload", response_model=CVResponse, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(None),
    interview_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a CV document (PDF, DOCX).
    Performs magic-byte validation, in-memory extraction with PaddleOCR fallback,
    saves the original document to disk, and records metadata in PostgreSQL.
    """
    filename = file.filename or "resume.pdf"
    file_bytes = await file.read()

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes)."
        )

    if len(file_bytes) > 15 * 1024 * 1024:  # 15MB limit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 15MB limit."
        )

    try:
        cv_record = await cv_service.process_and_store_cv(
            db=db,
            filename=filename,
            file_bytes=file_bytes,
            user_id=user_id,
            interview_id=interview_id,
        )
        return cv_record
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {exc}"
        )

@router.get("", response_model=List[CVResponse])
async def list_cvs(
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all stored CVs, optionally filtered by user_id."""
    return await cv_service.list_cvs(db, user_id=user_id)

@router.get("/{cv_id}", response_model=CVResponse)
async def get_cv(
    cv_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve parsed CV metadata and structured data by ID."""
    cv = await cv_service.get_cv(db, cv_id)
    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CV with ID '{cv_id}' was not found."
        )
    return cv

@router.get("/{cv_id}/download")
async def download_cv_document(
    cv_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Download the original uploaded PDF/DOCX document."""
    cv = await cv_service.get_cv(db, cv_id)
    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CV with ID '{cv_id}' was not found."
        )

    file_path = cv_service.get_absolute_file_path(cv)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original document file not found on storage server."
        )

    media_type = "application/pdf" if cv.file_type == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return FileResponse(
        path=str(file_path),
        filename=cv.file_name,
        media_type=media_type,
    )

@router.delete("/{cv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cv(
    cv_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a CV record and remove its original document file."""
    deleted = await cv_service.delete_cv(db, cv_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CV with ID '{cv_id}' was not found."
        )
    return None
