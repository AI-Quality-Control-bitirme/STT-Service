from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_call_repository
from app.models.call import Call
from app.models.transcription import Transcription
from app.repositories.call_repository import CallRepository
from app.schemas.call import CallCreate, CallRead
from app.schemas.transcription import TranscriptionCreate, TranscriptionRead

calls_router = APIRouter(prefix="/calls", tags=["calls"])
transcriptions_router = APIRouter(prefix="/transcriptions", tags=["transcriptions"])


@calls_router.post("", response_model=CallRead, status_code=status.HTTP_201_CREATED)
def create_call(
    payload: CallCreate,
    repository: CallRepository = Depends(get_call_repository),
) -> Call:
    return repository.create_call(payload)


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