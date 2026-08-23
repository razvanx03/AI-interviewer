import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, Enum as SAEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base import Base
from schemas.interview import ExperienceLevel, InterviewStatus

if TYPE_CHECKING:
    from models.message import Message
    from models.candidate import Candidate

class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Native PostgreSQL Enum for Experience Level
    experience_level: Mapped[ExperienceLevel] = mapped_column(
        SAEnum(
            ExperienceLevel,
            name="experience_level_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=ExperienceLevel.MID,
        nullable=False,
    )
    
    candidate_name: Mapped[str] = mapped_column(String(255), default="Candidate")
    cv_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cv_raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Native PostgreSQL Enum for Interview Status
    status: Mapped[InterviewStatus] = mapped_column(
        SAEnum(
            InterviewStatus,
            name="interview_status_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=InterviewStatus.ACTIVE,
        nullable=False,
    )

    # Conversational State & Topic Tracking
    active_question_number: Mapped[Optional[int]] = mapped_column(nullable=True, default=1)
    consecutive_clarifications: Mapped[int] = mapped_column(nullable=False, default=0)
    topics_plan: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=list)
    current_topic_index: Mapped[int] = mapped_column(nullable=False, default=0)
    topic_follow_up_count: Mapped[int] = mapped_column(nullable=False, default=0)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    # Relationships
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="interview", cascade="all, delete-orphan", order_by="Message.created_at"
    )
    candidates: Mapped[List["Candidate"]] = relationship(
        "Candidate", back_populates="interview", cascade="all, delete-orphan"
    )
