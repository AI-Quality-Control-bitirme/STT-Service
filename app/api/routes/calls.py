import logging
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.api.deps import get_call_repository, get_call_upload_service
from app.models.call import Call
from app.models.transcription import Transcription
from app.repositories.call_repository import CallRepository
from app.schemas.call import CallRead, CallUploadMetadata
from app.schemas.transcription import TranscriptionCreate, TranscriptionRead
from app.services.call_upload_service import AudioUploadError, CallUploadService

logger = logging.getLogger(__name__)

calls_router = APIRouter(prefix="/calls", tags=["calls"])
transcriptions_router = APIRouter(prefix="/transcriptions", tags=["transcriptions"])


@calls_router.post(
    "",
    response_model=CallRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a call recording (MP3) with metadata",
)
async def create_call(
    audio: Annotated[UploadFile, File(description="Call recording in MP3 format")],
    external_call_id: Annotated[str | None, Form()] = None,
    caller_number: Annotated[str | None, Form()] = None,
    callee_number: Annotated[str | None, Form()] = None,
    call_started_at: Annotated[datetime | None, Form()] = None,
    call_ended_at: Annotated[datetime | None, Form()] = None,
    duration_seconds: Annotated[int | None, Form()] = None,
    service: CallUploadService = Depends(get_call_upload_service),
) -> Call:
    try:
        metadata = CallUploadMetadata(
            external_call_id=external_call_id,
            caller_number=caller_number,
            callee_number=callee_number,
            call_started_at=call_started_at,
            call_ended_at=call_ended_at,
            duration_seconds=duration_seconds,
        )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors(include_url=False)) from exc

    try:
        return await service.create_call(audio, metadata)
    except AudioUploadError as exc:
        logger.warning("Rejected call upload %s: %s", audio.filename, exc)
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@calls_router.get("", response_model=list[CallRead])
def list_calls(
    repository: CallRepository = Depends(get_call_repository),
) -> list[Call]:
    return repository.list_calls()


@calls_router.get("/{call_id}", response_model=CallRead)
def get_call(
    call_id: UUID,
    repository: CallRepository = Depends(get_call_repository),
) -> Call:
    call = repository.get_call(call_id)
    if call is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )
    return call


@calls_router.post(
    "/{call_id}/transcriptions",
    response_model=TranscriptionRead,
    status_code=status.HTTP_201_CREATED,
)
def add_transcription(
    call_id: UUID,
    payload: TranscriptionCreate,
    repository: CallRepository = Depends(get_call_repository),
) -> Transcription:
    transcription = repository.add_transcription(call_id, payload)
    if transcription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )
    return transcription


@transcriptions_router.get("/{transcription_id}", response_model=TranscriptionRead)
def get_transcription(
    transcription_id: UUID,
    repository: CallRepository = Depends(get_call_repository),
) -> Transcription:
    transcription = repository.get_transcription(transcription_id)
    if transcription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcription not found",
        )
    return transcription


router = APIRouter()
router.include_router(calls_router)
router.include_router(transcriptions_router)