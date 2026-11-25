from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import ProcessingStatus
from app.repositories.call_repository import CallRepository
from app.schemas.call import CallCreate
from app.schemas.transcription import TranscriptionCreate


def _create_call(
    session: Session, status: ProcessingStatus = ProcessingStatus.PENDING
):
    return CallRepository(session).create_call(
        CallCreate(audio_file_ref="uploads/test.mp3", processing_status=status)
    )


def _add_transcription(session: Session, call_id, **fields):
    return CallRepository(session).add_transcription(
        call_id, TranscriptionCreate(**fields)
    )


def test_get_call_returns_processing_status(
    client: TestClient, db_session: Session
) -> None:
    call = _create_call(db_session, ProcessingStatus.PROCESSING)

    response = client.get(f"/calls/{call.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(call.id)
    assert response.json()["processing_status"] == "processing"


def test_get_call_unknown_id_returns_404(client: TestClient) -> None:
    response = client.get(f"/calls/{uuid4()}")
    assert response.status_code == 404


def test_get_call_invalid_id_returns_422(client: TestClient) -> None:
    response = client.get("/calls/not-a-uuid")
    assert response.status_code == 422


def test_transcript_returns_completed_text(
    client: TestClient, db_session: Session
) -> None:
    call = _create_call(db_session, ProcessingStatus.COMPLETED)
    transcription = _add_transcription(
        db_session,
        call.id,
        transcript_text="Merhaba, nasıl yardımcı olabilirim?",
        language="tr",
    )

    response = client.get(f"/calls/{call.id}/transcript")

    assert response.status_code == 200
    body = response.json()
    assert body["call_id"] == str(call.id)
    assert body["transcription_id"] == str(transcription.id)
    assert body["transcript_text"] == "Merhaba, nasıl yardımcı olabilirim?"
    assert body["language"] == "tr"


def test_transcript_uses_latest_transcription(
    client: TestClient, db_session: Session
) -> None:
    call = _create_call(db_session, ProcessingStatus.COMPLETED)
    older = _add_transcription(db_session, call.id, transcript_text="first run")
    newer = _add_transcription(db_session, call.id, transcript_text="second run")
    older.created_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_session.commit()

    response = client.get(f"/calls/{call.id}/transcript")

    assert response.status_code == 200
    assert response.json()["transcription_id"] == str(newer.id)
    assert response.json()["transcript_text"] == "second run"


def test_transcript_unknown_call_returns_404(client: TestClient) -> None:
    response = client.get(f"/calls/{uuid4()}/transcript")
    assert response.status_code == 404
    assert response.json()["detail"] == "Call not found"


def test_transcript_pending_call_without_transcription_returns_409(
    client: TestClient, db_session: Session
) -> None:
    call = _create_call(db_session, ProcessingStatus.PENDING)

    response = client.get(f"/calls/{call.id}/transcript")

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["processing_status"] == "pending"
    assert detail["call_id"] == str(call.id)
    assert detail["message"] == "Transcription is not ready yet"


def test_transcript_in_progress_returns_409(
    client: TestClient, db_session: Session
) -> None:
    call = _create_call(db_session, ProcessingStatus.PROCESSING)
    _add_transcription(
        db_session, call.id, processing_status=ProcessingStatus.PROCESSING
    )

    response = client.get(f"/calls/{call.id}/transcript")

    assert response.status_code == 409
    assert response.json()["detail"]["processing_status"] == "processing"


def test_transcript_failed_returns_409_with_error(
    client: TestClient, db_session: Session
) -> None:
    call = _create_call(db_session, ProcessingStatus.FAILED)
    _add_transcription(
        db_session,
        call.id,
        processing_status=ProcessingStatus.FAILED,
        error_message="provider timeout",
    )

    response = client.get(f"/calls/{call.id}/transcript")

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["processing_status"] == "failed"
    assert detail["message"] == "Transcription failed"
    assert detail["error_message"] == "provider timeout"


def test_transcript_completed_call_without_text_returns_404(
    client: TestClient, db_session: Session
) -> None:
    call = _create_call(db_session, ProcessingStatus.COMPLETED)

    response = client.get(f"/calls/{call.id}/transcript")

    assert response.status_code == 404
    assert response.json()["detail"] == "Transcript not found for this call"
