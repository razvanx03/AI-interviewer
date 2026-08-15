from pydantic import BaseModel
from typing import Optional, List

class CVParseResult(BaseModel):
    filename: str
    file_size_bytes: int
    content_type: str
    extracted_text: str
    extracted_skills: List[str] = []
    extracted_experience_years: Optional[int] = None
    summary: Optional[str] = None
