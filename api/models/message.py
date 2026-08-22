import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base import Base
from schemas.chat import MessageRole

if TYPE_CHECKING:
    from models.interview import Interview

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    interview_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interviews.id", ondelete="CASCADE"), index=True, nullable=False
    )
    
    # Native PostgreSQL Enum for Message Role
    role: Mapped[MessageRole] = mapped_column(
        SAEnum(
            MessageRole,
            name="message_role_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    
    content: Mapped[str] = mapped_column(Text, nullable=False)
    question_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # Relationships
    interview: Mapped["Interview"] = relationship("Interview", back_populates="messages")
