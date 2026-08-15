from fastapi import APIRouter, HTTPException, status
from typing import List
from schemas.interview import InterviewCreate, InterviewResponse
from schemas.chat import ChatMessage
from services.interview_service import interview_service

router = APIRouter()

@router.post("", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
def create_interview(data: InterviewCreate):
    """Create a new interview session with job information and CV details."""
    session = interview_service.create_interview(data)
    return session

@router.get("/{interview_id}", response_model=InterviewResponse)
def get_interview(interview_id: str):
    """Fetch an interview session by unique shareable ID."""
    session = interview_service.get_interview(interview_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Interview with ID '{interview_id}' was not found"
        )
    return session

@router.get("/{interview_id}/messages", response_model=List[ChatMessage])
def get_interview_messages(interview_id: str):
    """Retrieve full chat history for an interview session."""
    session = interview_service.get_interview(interview_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Interview with ID '{interview_id}' was not found"
        )
    return session.messages
