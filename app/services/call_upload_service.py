import logging
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.call import Call
from app.models.enums import ProcessingStatus
from app.repositories.call_repository import CallRepository
from app.schemas.call import CallCreate, CallUploadMetadata

logger = logging.getLogger(__name__)

MP3_CONTENT_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/mpeg3",
    "audio/x-mpeg-3",
    "application/octet-stream",
}


class AudioUploadError(ValueError):
    status_code = 422


class UnsupportedAudioError(AudioUploadError):
    status_code = 415


class AudioTooLargeError(AudioUploadError):
    status_code = 413


def looks_like_mp3(head: bytes) -> bool:
    if head.startswith(b"ID3"):
        return True
    return len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0


class CallUploadService:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._repository = CallRepository(session)

    def _upload_dir(self) -> Path:
        path = Path(self._settings.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    async def _read_mp3(self, upload: UploadFile) -> bytes:
        filename = upload.filename or ""
        content_type = (upload.content_type or "").lower()
        if Path(filename).suffix.lower() != ".mp3":
            raise UnsupportedAudioError("Only .mp3 files are accepted")
        if content_type and content_type not in MP3_CONTENT_TYPES:
            raise UnsupportedAudioError(
                f"Unsupported content type {content_type!r}; expected audio/mpeg"
            )

        max_bytes = self._settings.max_upload_size_mb * 1024 * 1024
        content = await upload.read(max_bytes + 1)
        if len(content) == 0:
            raise AudioUploadError("Uploaded audio file is empty")
        if len(content) > max_bytes:
            raise AudioTooLargeError(
                f"Upload exceeds maximum size of {self._settings.max_upload_size_mb} MB"
            )
        if not looks_like_mp3(content[:3]):
            raise UnsupportedAudioError("File content is not a valid MP3 stream")
        return content

    async def create_call(
        self, upload: UploadFile, metadata: CallUploadMetadata
    ) -> Call:
        content = await self._read_mp3(upload)

        call_id = uuid.uuid4()
        dest = self._upload_dir() / f"{call_id}.mp3"
        dest.write_bytes(content)
        try:
            call = self._repository.create_call(
                CallCreate(
                    audio_file_ref=str(dest),
                    processing_status=ProcessingStatus.PENDING,
                    **metadata.model_dump(),
                ),
                call_id=call_id,
            )
        except Exception:
            dest.unlink(missing_ok=True)
            raise

        logger.info("Stored call %s audio at %s (%s bytes)", call_id, dest, len(content))
        return call
