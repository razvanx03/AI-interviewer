from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from db.base import Base

class CVChunk(Base):
    """
    Relational model storing chunked CV text segments and their semantic embeddings
    for pgvector similarity search in RAG candidate screening.
    """
    __tablename__ = "cv_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    candidate_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    candidate_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cv_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(768), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
