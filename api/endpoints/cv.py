from fastapi import APIRouter, UploadFile, File, HTTPException, status
from schemas.cv import CVParseResult
from services.cv_service import cv_service

router = APIRouter()

@router.post("/upload", response_model=CVParseResult)
async def upload_cv(file: UploadFile = File(...)):
    """
    Upload CV document (PDF, DOCX) and extract text/metadata.
    Uses mock extraction parser now; PyMuPDF/python-docx will plug in cleanly here.
    """
    allowed_extensions = [".pdf", ".docx", ".doc", ".txt"]
    filename = file.filename or "resume.pdf"
    
    if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload PDF, DOCX, or TXT file."
        )

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 10MB limit."
        )

    result = await cv_service.parse_cv_file(
        filename=filename,
        file_bytes=file_bytes,
        content_type=file.content_type or "application/octet-stream"
    )
    return result
