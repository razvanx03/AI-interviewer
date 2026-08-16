from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from schemas.interview import InterviewCreate, InterviewResponse
from schemas.chat import ChatMessage
from services.interview_service import interview_service

router = APIRouter()

@router.post("", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
async def create_interview(data: InterviewCreate, db: AsyncSession = Depends(get_db)):
    """Create a new interview session in PostgreSQL and generate the initial question."""
    interview = await interview_service.create_interview(db, data)
    return interview

@router.get("", response_model=List[InterviewResponse])
async def list_interviews(
    ids: Optional[str] = Query(None, description="Comma-separated list of interview IDs"),
    db: AsyncSession = Depends(get_db),
):
    """List interviews, optionally filtered by comma-separated IDs stored in localStorage."""
    id_list = [i.strip() for i in ids.split(",")] if ids else None
    interviews = await interview_service.list_interviews(db, id_list)
    return interviews

@router.get("/{interview_id}", response_model=InterviewResponse)
async def get_interview(interview_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch an interview session by unique ID."""
    interview = await interview_service.get_interview(db, interview_id)
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview with ID '{interview_id}' was not found",
        )
    return interview

@router.get("/{interview_id}/messages", response_model=List[ChatMessage])
async def get_interview_messages(interview_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve full chat history for an interview session from PostgreSQL."""
    interview = await interview_service.get_interview(db, interview_id)
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview with ID '{interview_id}' was not found",
        )
    messages = await interview_service.get_messages(db, interview_id)
    return messages

@router.post("/{interview_id}/complete", response_model=InterviewResponse)
async def complete_interview(interview_id: str, db: AsyncSession = Depends(get_db)):
    """Mark an active interview as completed in PostgreSQL and append closing message."""
    interview = await interview_service.complete_interview(db, interview_id)
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview with ID '{interview_id}' was not found",
        )
    return interview

@router.delete("/{interview_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interview(interview_id: str, db: AsyncSession = Depends(get_db)):
    """Delete an interview and all associated messages from the database."""
    deleted = await interview_service.delete_interview(db, interview_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview with ID '{interview_id}' was not found",
        )
    return None
