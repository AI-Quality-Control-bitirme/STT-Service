from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ProcessingStatus

if TYPE_CHECKING:
    from app.models.transcription import Transcription


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    external_call_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    caller_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    callee_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    audio_file_ref: Mapped[str] = mapped_column(Text, nullable=False)
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, name="processing_status", native_enum=False),
        nullable=False,
        default=ProcessingStatus.PENDING,
    )
    call_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    call_ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    transcriptions: Mapped[list[Transcription]] = relationship(
        "Transcription",
        back_populates="call",
        cascade="all, delete-orphan",
    )