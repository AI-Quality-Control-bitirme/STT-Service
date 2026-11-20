from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.call import Call
from app.models.transcription import Transcription
from app.schemas.call import CallCreate
from app.schemas.transcription import TranscriptionCreate


class CallRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_call(self, data: CallCreate) -> Call:
        call = Call(
            audio_file_ref=data.audio_file_ref,
            external_call_id=data.external_call_id,
            caller_number=data.caller_number,
            callee_number=data.callee_number,
            call_started_at=data.call_started_at,
            call_ended_at=data.call_ended_at,
            duration_seconds=data.duration_seconds,
            processing_status=data.processing_status,
        )
        self._session.add(call)
        self._session.commit()
        self._session.refresh(call)
        return call

    def get_call(self, call_id: UUID) -> Call | None:
        stmt = (
            select(Call)
            .where(Call.id == call_id)
            .options(selectinload(Call.transcriptions))
        )
        return self._session.scalar(stmt)

    def list_calls(self) -> list[Call]:
        stmt = select(Call).options(selectinload(Call.transcriptions)).order_by(
            Call.created_at.desc()
        )
        return list(self._session.scalars(stmt).all())

    def add_transcription(
        self, call_id: UUID, data: TranscriptionCreate
    ) -> Transcription | None:
        call = self.get_call(call_id)
        if call is None:
            return None
        transcription = Transcription(
            call_id=call_id,
            transcript_text=data.transcript_text,
            language=data.language,
            processing_status=data.processing_status,
            error_message=data.error_message,
        )
        self._session.add(transcription)
        self._session.commit()
        self._session.refresh(transcription)
        return transcription

    def get_transcription(self, transcription_id: UUID) -> Transcription | None:
        stmt = select(Transcription).where(Transcription.id == transcription_id)
        return self._session.scalar(stmt)