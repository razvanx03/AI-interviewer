from db.base import Base
from models.interview import Interview
from models.message import Message
from models.candidate import Candidate
from models.cv import CV, ParsingStatus

__all__ = ["Base", "Interview", "Message", "Candidate", "CV", "ParsingStatus"]
