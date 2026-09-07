from pydantic import BaseModel
from typing import List, Optional

class ExtractedCandidateItem(BaseModel):
    filename: str
    file_type: str
    raw_text: str
    extracted_name: Optional[str] = None
    file_size: int

class BatchExtractResponse(BaseModel):
    candidates: List[ExtractedCandidateItem]
