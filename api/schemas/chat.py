from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    SYSTEM = "system"
    ASSISTANT = "assistant"
    USER = "user"

class ChatMessage(BaseModel):
    id: str
    role: MessageRole
    content: str
    created_at: datetime
    feedback: Optional[str] = None
    question_number: Optional[int] = None

class ChatRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Candidate's response/message")

class ChatResponse(BaseModel):
    message: ChatMessage
    is_complete: bool = False
    next_question_number: Optional[int] = None
