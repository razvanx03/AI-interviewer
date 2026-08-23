from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from models.cv import ParsingStatus

class CVParseResult(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size_bytes: int
    storage_path: str
    extracted_text: str
    parsed_data: Dict[str, Any] = Field(default_factory=dict)
    parsing_status: ParsingStatus
    created_at: datetime

    class Config:
        from_attributes = True

class CVResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    interview_id: Optional[str] = None
    file_name: str
    file_type: str
    file_size: int
    storage_path: str
    raw_text: str
    parsed_data: Optional[Dict[str, Any]] = None
    parsing_status: ParsingStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
