from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ProcessingStatus
from app.schemas.transcription import TranscriptionRead


class CallCreate(BaseModel):
    audio_file_ref: str = Field(..., min_length=1)
    external_call_id: str | None = None
    caller_number: str | None = None
    callee_number: str | None = None
    call_started_at: datetime | None = None
    call_ended_at: datetime | None = None
    duration_seconds: int | None = None
    processing_status: ProcessingStatus = ProcessingStatus.PENDING


class CallRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_call_id: str | None
    caller_number: str | None
    callee_number: str | None
    audio_file_ref: str
    processing_status: ProcessingStatus
    call_started_at: datetime | None
    call_ended_at: datetime | None
    duration_seconds: int | None
    created_at: datetime
    updated_at: datetime
    transcriptions: list[TranscriptionRead] = Field(default_factory=list)