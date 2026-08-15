from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class InterviewStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"

class ExperienceLevel(str, Enum):
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    EXECUTIVE = "executive"

class InterviewCreate(BaseModel):
    job_title: str = Field(..., description="Job role/title (e.g. Senior Backend Engineer)")
    company_name: Optional[str] = Field(None, description="Company name")
    job_description: str = Field(..., description="Job description or list of requirements")
    experience_level: ExperienceLevel = Field(default=ExperienceLevel.MID, description="Seniority level")
    candidate_name: Optional[str] = Field("Candidate", description="Candidate's name")
    cv_filename: Optional[str] = Field(None, description="Uploaded CV filename")
    cv_raw_text: Optional[str] = Field(None, description="Extracted text from CV")

class InterviewResponse(BaseModel):
    id: str
    job_title: str
    company_name: Optional[str] = None
    job_description: str
    experience_level: ExperienceLevel
    candidate_name: Optional[str] = "Candidate"
    cv_filename: Optional[str] = None
    status: InterviewStatus = InterviewStatus.ACTIVE
    created_at: datetime
    updated_at: datetime
    total_questions: int = 0

    class Config:
        from_attributes = True
