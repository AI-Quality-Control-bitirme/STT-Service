import logging
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.call import Call
from app.models.enums import ProcessingStatus
from app.models.transcription import Transcription
from app.repositories.call_repository import CallRepository
from app.schemas.call import CallCreate
from app.schemas.transcription import TranscriptionCreate
from app.services.stt.base import SttProviderError
from app.services.stt.factory import get_stt_provider

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "audio/ogg",
    "audio/flac",
    "audio/mp4",
    "audio/x-m4a",
    "application/octet-stream",
}


class TranscriptionService:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._repository = CallRepository(session)
        self._session = session

    def _upload_dir(self) -> Path:
        path = Path(self._settings.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    async def save_upload(self, upload: UploadFile) -> Path:
        suffix = Path(upload.filename or "audio.bin").suffix or ".bin"
        dest = self._upload_dir() / f"{uuid.uuid4()}{suffix}"
        content = await upload.read()
        max_bytes = self._settings.max_upload_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise ValueError(
                f"Upload exceeds maximum size of {self._settings.max_upload_size_mb} MB"
            )
        if len(content) == 0:
            raise ValueError("Uploaded audio file is empty")
        content_type = (upload.content_type or "").lower()
        if content_type and content_type not in ALLOWED_CONTENT_TYPES:
            logger.warning(
                "Unexpected audio content-type %s for %s; proceeding",
                content_type,
                upload.filename,
            )
        dest.write_bytes(content)
        logger.info("Saved upload to %s (%s bytes)", dest, len(content))
        return dest

    def transcribe_upload(
        self,
        audio_path: Path,
        *,
        caller_number: str | None = None,
        callee_number: str | None = None,
        external_call_id: str | None = None,
    ) -> tuple[Call, Transcription]:
        call = self._repository.create_call(
            CallCreate(
                audio_file_ref=str(audio_path),
                caller_number=caller_number,
                callee_number=callee_number,
                external_call_id=external_call_id,
                processing_status=ProcessingStatus.PROCESSING,
            )
        )
        transcription = self._repository.add_transcription(
            call.id,
            TranscriptionCreate(processing_status=ProcessingStatus.PROCESSING),
        )
        assert transcription is not None

        try:
            provider = get_stt_provider(self._settings)
            result = provider.transcribe(audio_path)
        except (SttProviderError, ValueError) as exc:
            logger.error(
                "STT provider failed for call %s: %s",
                call.id,
                exc,
                exc_info=isinstance(exc, SttProviderError),
            )
            self._repository.update_transcription(
                transcription.id,
                processing_status=ProcessingStatus.FAILED,
                error_message=str(exc),
            )
            self._repository.update_call(
                call.id,
                processing_status=ProcessingStatus.FAILED,
            )
            self._session.refresh(call)
            self._session.refresh(transcription)
            return call, transcription

        self._repository.update_transcription(
            transcription.id,
            transcript_text=result.text,
            language=result.language,
            processing_status=ProcessingStatus.COMPLETED,
            clear_error=True,
        )
        self._repository.update_call(
            call.id,
            processing_status=ProcessingStatus.COMPLETED,
        )
        refreshed = self._repository.get_call(call.id)
        assert refreshed is not None
        latest = refreshed.transcriptions[-1]
        return refreshed, latest