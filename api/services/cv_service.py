import os
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.cv import CV, ParsingStatus
from schemas.cv import CVParseResult
from .document_extractor import document_extractor
from .cv_parser import cv_parser

logger = logging.getLogger("api.services.cv")

class CVService:
    """
    Orchestration service for candidate CV lifecycle:
    1. Validation (magic bytes + format)
    2. In-memory document extraction with PaddleOCR fallback
    3. LLM-based structured data parsing
    4. Original document filesystem storage & PostgreSQL persistence
    """

    def __init__(self, storage_dir: Optional[str] = None):
        base_path = Path(__file__).resolve().parent.parent.parent
        self.storage_dir = Path(storage_dir) if storage_dir else (base_path / settings.STORAGE_DIR)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def process_and_store_cv(
        self,
        db: AsyncSession,
        filename: str,
        file_bytes: bytes,
        user_id: Optional[str] = None,
        interview_id: Optional[str] = None,
    ) -> CV:
        """
        Processes an uploaded CV (PDF/DOCX), extracts text in-memory, parses structured data,
        saves the original document to storage, and persists the record in PostgreSQL.
        """
        # 1. Extract text in-memory (validates magic bytes & format)
        raw_text, file_type = document_extractor.extract_text(filename, file_bytes)

        # 2. Parse structured data via LLM
        parsed_data = await cv_parser.parse_cv_text(raw_text, filename)

        # 3. Save original file to persistent storage
        cv_id = str(uuid.uuid4())[:8]
        ext = f".{file_type}"
        saved_filename = f"{cv_id}{ext}"
        target_file_path = self.storage_dir / saved_filename
        
        with open(target_file_path, "wb") as f:
            f.write(file_bytes)

        relative_storage_path = f"{settings.STORAGE_DIR}/{saved_filename}"

        # 4. Persist in PostgreSQL
        now = datetime.now(timezone.utc)
        cv_record = CV(
            id=cv_id,
            user_id=user_id,
            interview_id=interview_id,
            file_name=filename,
            file_type=file_type,
            file_size=len(file_bytes),
            storage_path=relative_storage_path,
            raw_text=raw_text,
            parsed_data=parsed_data,
            parsing_status=ParsingStatus.COMPLETED,
            created_at=now,
            updated_at=now,
        )

        db.add(cv_record)
        await db.commit()
        await db.refresh(cv_record)

        logger.info("CV [%s] successfully processed, stored at [%s], and recorded in database.", cv_id, relative_storage_path)
        return cv_record

    async def get_cv(self, db: AsyncSession, cv_id: str) -> Optional[CV]:
        """Fetch CV record by ID."""
        stmt = select(CV).where(CV.id == cv_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_cvs(self, db: AsyncSession, user_id: Optional[str] = None) -> List[CV]:
        """List all CVs, optionally filtered by user_id."""
        stmt = select(CV).order_by(CV.created_at.desc())
        if user_id:
            stmt = stmt.where(CV.user_id == user_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    def get_absolute_file_path(self, cv: CV) -> Path:
        """Get absolute path to stored original document on filesystem."""
        base_path = Path(__file__).resolve().parent.parent.parent
        return base_path / cv.storage_path

    async def delete_cv(self, db: AsyncSession, cv_id: str) -> bool:
        """Delete CV from database and remove original stored file."""
        cv = await self.get_cv(db, cv_id)
        if not cv:
            return False

        # Remove physical file if exists
        try:
            file_path = self.get_absolute_file_path(cv)
            if file_path.exists():
                file_path.unlink()
        except Exception as exc:
            logger.warning("Failed to delete physical file for CV [%s]: %s", cv_id, exc)

        stmt = delete(CV).where(CV.id == cv_id)
        await db.execute(stmt)
        await db.commit()
        return True

cv_service = CVService()
