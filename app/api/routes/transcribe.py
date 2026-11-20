import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from app.api.deps import get_transcription_service
from app.schemas.transcribe import TranscribeResponse
from app.services.transcription_service import TranscriptionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transcribe", tags=["transcription"])


@router.post(
    "",
    response_model=TranscribeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload audio and transcribe",
)
async def transcribe_audio(
    audio: Annotated[UploadFile, File(description="Audio file to transcribe")],
    caller_number: Annotated[str | None, Form()] = None,
    callee_number: Annotated[str | None, Form()] = None,
    external_call_id: Annotated[str | None, Form()] = None,
    service: TranscriptionService = Depends(get_transcription_service),
) -> TranscribeResponse:
    try:
        audio_path = await service.save_upload(audio)
        call, transcription = service.transcribe_upload(
            audio_path,
            caller_number=caller_number,
            callee_number=callee_number,
            external_call_id=external_call_id,
        )
    except ValueError as exc:
        logger.warning("Invalid transcribe request: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    from app.schemas.call import CallRead
    from app.schemas.transcription import TranscriptionRead

    return TranscribeResponse(
        call=CallRead.model_validate(call),
        transcription=TranscriptionRead.model_validate(transcription),
    )