from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
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

class CandidateItem(BaseModel):
    name: str = Field(..., description="Candidate full name")
    cv_filename: Optional[str] = Field(None, description="Filename of candidate CV")
    cv_raw_text: Optional[str] = Field(None, description="Raw or parsed text content of candidate CV")

class CandidateScreeningResult(BaseModel):
    name: str
    match_score: int = Field(..., ge=0, le=100, description="Match score from 0 to 100")
    strengths: List[str] = Field(default_factory=list, description="Key candidate strengths relevant to job")
    summary: str = Field(..., description="Short screening summary of candidate")
    is_selected: bool = Field(False, description="True if chosen as the winning candidate")

class InterviewCreate(BaseModel):
    job_title: str = Field(..., description="Job role/title (e.g. Senior Backend Engineer)")
    company_name: Optional[str] = Field(None, description="Company name")
    job_description: str = Field(..., description="Job description or list of requirements")
    experience_level: ExperienceLevel = Field(default=ExperienceLevel.MID, description="Seniority level")
    # Multi-candidate pool
    candidates: Optional[List[CandidateItem]] = Field(None, description="Pool of candidates to screen")
    # Single candidate fallback (backward compatibility)
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
    cv_raw_text: Optional[str] = None
    candidates_pool: Optional[List[Dict[str, Any]]] = None
    screening_results: Optional[List[Dict[str, Any]]] = None
    status: InterviewStatus = InterviewStatus.ACTIVE
    created_at: datetime
    updated_at: datetime
    total_questions: int = 0

    class Config:
        from_attributes = True
