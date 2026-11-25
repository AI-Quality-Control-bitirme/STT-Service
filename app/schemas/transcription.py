from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ProcessingStatus


class TranscriptionCreate(BaseModel):
    transcript_text: str | None = None
    language: str | None = None
    processing_status: ProcessingStatus = ProcessingStatus.COMPLETED
    error_message: str | None = None


class TranscriptRead(BaseModel):
    call_id: UUID
    transcription_id: UUID
    transcript_text: str
    language: str | None
    created_at: datetime
    updated_at: datetime


class TranscriptUnavailable(BaseModel):
    message: str
    call_id: UUID
    processing_status: ProcessingStatus
    error_message: str | None = None


class TranscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    call_id: UUID
    transcript_text: str | None
    language: str | None
    processing_status: ProcessingStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime