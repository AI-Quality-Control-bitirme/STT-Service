from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

MP3_BYTES = b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\xff\xfb\x90\x64" + b"\x00" * 256


def _upload(client: TestClient, content: bytes = MP3_BYTES, **kwargs):
    filename = kwargs.pop("filename", "call-001.mp3")
    content_type = kwargs.pop("content_type", "audio/mpeg")
    return client.post(
        "/calls",
        files={"audio": (filename, content, content_type)},
        data=kwargs,
    )


def test_upload_stores_audio_and_records_pending_status(
    client: TestClient, upload_dir: Path
) -> None:
    response = _upload(
        client,
        caller_number="+905551234567",
        callee_number="+902321234567",
        external_call_id="pbx-42",
        call_started_at="2026-11-20T10:00:00Z",
        call_ended_at="2026-11-20T10:05:00Z",
        duration_seconds="300",
    )

    assert response.status_code == 201
    body = response.json()
    call_id = UUID(body["id"])
    assert body["processing_status"] == "pending"
    assert body["caller_number"] == "+905551234567"
    assert body["external_call_id"] == "pbx-42"
    assert body["duration_seconds"] == 300
    assert body["transcriptions"] == []

    stored = Path(body["audio_file_ref"])
    assert stored == upload_dir / f"{call_id}.mp3"
    assert stored.read_bytes() == MP3_BYTES

    fetched = client.get(f"/calls/{call_id}")
    assert fetched.status_code == 200
    assert fetched.json()["processing_status"] == "pending"


def test_each_upload_gets_a_unique_call_id(client: TestClient) -> None:
    first = _upload(client).json()["id"]
    second = _upload(client).json()["id"]
    assert first != second


def test_metadata_is_optional(client: TestClient) -> None:
    response = _upload(client)
    assert response.status_code == 201
    assert response.json()["caller_number"] is None


def test_rejects_non_mp3_extension(client: TestClient, upload_dir: Path) -> None:
    response = _upload(client, filename="call.wav", content_type="audio/wav")
    assert response.status_code == 415
    assert not upload_dir.exists() or not any(upload_dir.iterdir())


def test_rejects_wrong_content_type(client: TestClient) -> None:
    response = _upload(client, content_type="text/plain")
    assert response.status_code == 415


def test_rejects_content_that_is_not_mp3(client: TestClient) -> None:
    response = _upload(client, content=b"RIFF\x00\x00\x00\x00WAVEfmt ")
    assert response.status_code == 415
    assert "MP3" in response.json()["detail"]


def test_rejects_empty_file(client: TestClient) -> None:
    response = _upload(client, content=b"")
    assert response.status_code == 422


def test_rejects_file_over_size_limit(client: TestClient) -> None:
    too_big = MP3_BYTES + b"\x00" * (1024 * 1024)
    response = _upload(client, content=too_big)
    assert response.status_code == 413


def test_rejects_missing_file(client: TestClient) -> None:
    response = client.post("/calls", data={"caller_number": "+905551234567"})
    assert response.status_code == 422


def test_rejects_end_before_start(client: TestClient) -> None:
    response = _upload(
        client,
        call_started_at="2026-11-20T10:05:00Z",
        call_ended_at="2026-11-20T10:00:00Z",
    )
    assert response.status_code == 422


def test_rejects_negative_duration(client: TestClient) -> None:
    response = _upload(client, duration_seconds="-5")
    assert response.status_code == 422


def test_rejects_invalid_timestamp(client: TestClient) -> None:
    response = _upload(client, call_started_at="yesterday")
    assert response.status_code == 422
