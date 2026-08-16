import datetime
from typing import List, Optional
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base import Base

class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    experience_level: Mapped[str] = mapped_column(String(50), default="mid")
    candidate_name: Mapped[str] = mapped_column(String(255), default="Candidate")
    cv_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cv_raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cv_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")  # 'active' | 'completed'
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
