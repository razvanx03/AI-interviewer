import datetime
from enum import Enum
from typing import Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base import Base

if TYPE_CHECKING:
    from models.interview import Interview

class ParsingStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class CV(Base):
    __tablename__ = "cvs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    interview_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("interviews.id", ondelete="SET NULL"), index=True, nullable=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # 'pdf' or 'docx'
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    parsing_status: Mapped[ParsingStatus] = mapped_column(
        SAEnum(
            ParsingStatus,
            name="parsing_status_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=ParsingStatus.PENDING,
        nullable=False,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    # Relationships
    interview: Mapped[Optional["Interview"]] = relationship("Interview", backref="cv_records")
