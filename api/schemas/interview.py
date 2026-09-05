from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime
from enum import Enum

class InterviewStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    FINISHING = "finishing"
    COMPLETED = "completed"

class ExperienceLevel(str, Enum):
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    EXECUTIVE = "executive"

class CandidateItem(BaseModel):
    id: Optional[str] = Field(None, description="Unique candidate ID")
    name: str = Field(..., description="Candidate full name")
    cv_filename: Optional[str] = Field(None, description="Filename of candidate CV")
    cv_raw_text: Optional[str] = Field(None, description="Raw or parsed text content of candidate CV")

class CandidateScreeningResult(BaseModel):
    id: Optional[str] = Field(None, description="Unique candidate ID")
    name: str
    match_score: int = Field(..., ge=0, le=100, description="Match score from 0 to 100")
    strengths: List[str] = Field(default_factory=list, description="Key candidate strengths relevant to job")
    gaps: Optional[List[str]] = Field(default_factory=list, description="Identified candidate gaps relative to JD")
    matched_chunks: Optional[List[str]] = Field(default_factory=list, description="Top semantic CV chunks retrieved via pgvector")
    summary: str = Field(..., description="Short screening summary of candidate")
    is_selected: bool = Field(False, description="True if chosen as the winning candidate")
    cv_filename: Optional[str] = None
    cv_raw_text: Optional[str] = None
    experience_years: Optional[float] = Field(None, description="Verified total professional work experience in years")
    timeline_summary: Optional[str] = Field(None, description="Detailed employment timeline summary")
    tech_tenure: Optional[Dict[str, float]] = Field(default_factory=dict, description="Tenure per technology in years")
    work_history: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Structured employment history blocks")

class CandidateScreeningRequest(BaseModel):
    job_title: str = Field(..., description="Job role/title")
    company_name: Optional[str] = Field(None, description="Company name")
    job_description: str = Field(..., description="Job requirements")
    experience_level: ExperienceLevel = Field(default=ExperienceLevel.MID, description="Seniority level")
    candidates: List[CandidateItem] = Field(..., min_length=1, max_length=150, description="List of candidate resumes")

class CandidateScreeningResponse(BaseModel):
    top_candidate: Dict[str, Any]
    screening_results: List[CandidateScreeningResult]

class CandidateResponse(BaseModel):
    id: str
    interview_id: str
    name: str
    cv_filename: Optional[str] = None
    cv_raw_text: Optional[str] = None
    match_score: Optional[int] = None
    strengths: Optional[List[str]] = None
    summary: Optional[str] = None
    is_selected: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

class InterviewCreate(BaseModel):
    job_title: str = Field(..., description="Job role/title (e.g. Senior Backend Engineer)")
    company_name: Optional[str] = Field(None, description="Company name")
    job_description: str = Field(..., description="Job description or list of requirements")
    experience_level: ExperienceLevel = Field(default=ExperienceLevel.MID, description="Seniority level")
    candidates: Optional[List[CandidateItem]] = Field(None, description="Pool of candidates to screen")
    candidate_name: Optional[str] = Field("Candidate", description="Candidate's name")
    cv_filename: Optional[str] = Field(None, description="Uploaded CV filename")
    cv_raw_text: Optional[str] = Field(None, description="Extracted text from CV")
    time_limit_minutes: Optional[int] = Field(None, ge=10, le=120, description="Optional interview time limit in minutes")
    language: Optional[str] = Field("en", description="Interview spoken language (en or ro)")

class InterviewResponse(BaseModel):
    id: str
    job_title: str
    company_name: Optional[str] = None
    job_description: str
    experience_level: ExperienceLevel
    candidate_name: Optional[str] = "Candidate"
    cv_filename: Optional[str] = None
    status: InterviewStatus = InterviewStatus.ACTIVE
    active_question_number: Optional[int] = None
    active_question_text: Optional[str] = None
    active_question_status: Optional[str] = "INTRO"
    topics_plan: Optional[List[str]] = None
    assessed_topics: Optional[List[str]] = None
    time_limit_minutes: Optional[int] = None
    language: Optional[str] = "en"
    conversation_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    total_questions: int = 0

    class Config:
        from_attributes = True
