from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.call_repository import CallRepository
from app.services.call_upload_service import CallUploadService
from app.services.transcription_service import TranscriptionService


def get_call_repository(
    session: Session = Depends(get_db),
) -> CallRepository:
    return CallRepository(session)


def get_call_upload_service(
    session: Session = Depends(get_db),
) -> CallUploadService:
    return CallUploadService(session)


def get_transcription_service(
    session: Session = Depends(get_db),
) -> TranscriptionService:
    return TranscriptionService(session)