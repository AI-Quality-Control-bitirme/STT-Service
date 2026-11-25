# STT-Service

Speech-to-text conversion service for the AI Quality Control platform.

## Project structure

```
STT-Service/
├── alembic/                 # Database migrations
│   └── versions/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── api/
│   │   ├── deps.py
│   │   └── routes/
│   │       ├── health.py
│   │       ├── calls.py
│   │       └── transcribe.py  # Upload + STT (SCRUM-56)
│   ├── services/
│   │   └── stt/             # local faster-whisper, OpenAI Whisper, mock (tests)
│   ├── core/
│   │   └── config.py
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── models/              # SQLAlchemy models (calls, transcriptions)
│   ├── repositories/
│   └── schemas/             # Pydantic request/response models
├── .env.example
├── alembic.ini
├── requirements.txt
└── README.md
```

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- **ffmpeg** (recommended for decoding non-WAV uploads; `faster-whisper` uses PyAV)

## Setup

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

   The first local transcription downloads the Whisper weights from Hugging Face
   (default model size `tiny`, ~75 MB). No API key is required.

3. Copy environment configuration:

   ```bash
   cp .env.example .env
   ```

   | Variable                   | Default                                                          | Description                        |
   |----------------------------|--------------------------------------------------------------------|------------------------------------|
   | `APP_NAME`                 | STT Service                                                        | Application display name           |
   | `APP_ENV`                  | development                                                        | Environment label                  |
   | `DEBUG`                    | true                                                               | Enable debug mode                  |
   | `HOST`                     | 0.0.0.0                                                            | Bind host                          |
   | `PORT`                     | 8000                                                               | Bind port                          |
   | `DATABASE_URL`             | postgresql+psycopg://stt_user:stt_pass@localhost:5432/stt_db     | PostgreSQL connection              |
   | `STT_PROVIDER`             | local                                                              | `local`, `openai`, or `mock`       |
   | `LOCAL_WHISPER_MODEL`      | tiny                                                               | faster-whisper size: tiny/base/...  |
   | `LOCAL_WHISPER_DEVICE`     | cpu                                                                | `cpu` or `cuda`                    |
   | `LOCAL_WHISPER_COMPUTE_TYPE` | int8                                                             | int8 / float16 / ...               |
   | `OPENAI_API_KEY`           | (unset)                                                            | Required when `STT_PROVIDER=openai`|
   | `UPLOAD_DIR`               | uploads                                                            | Stored audio files                 |

4. Create the database (once) and run migrations:

   ```bash
   alembic upgrade head
   ```

## Database schema

**`calls`** — call metadata and audio reference

| Column               | Type        | Notes                              |
|----------------------|-------------|------------------------------------|
| `id`                 | UUID (PK)   |                                    |
| `external_call_id`   | string      | Optional external reference        |
| `caller_number`      | string      |                                    |
| `callee_number`      | string      |                                    |
| `audio_file_ref`     | text        | Path or URI to audio file          |
| `processing_status`  | enum        | pending / processing / completed / failed |
| `call_started_at`    | timestamptz |                                    |
| `call_ended_at`      | timestamptz |                                    |
| `duration_seconds`   | integer     |                                    |
| `created_at`         | timestamptz |                                    |
| `updated_at`         | timestamptz |                                    |

**`transcriptions`** — transcription results linked to a call

| Column               | Type        | Notes                              |
|----------------------|-------------|------------------------------------|
| `id`                 | UUID (PK)   |                                    |
| `call_id`            | UUID (FK)   | References `calls.id`              |
| `transcript_text`    | text        |                                    |
| `language`           | string      |                                    |
| `processing_status`  | enum        | pending / processing / completed / failed |
| `error_message`      | text        | Set when status is failed          |
| `created_at`         | timestamptz |                                    |
| `updated_at`         | timestamptz |                                    |

Speaker diarization is **not** implemented; transcripts are plain full-utterance text.

## Startup

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs: `http://localhost:8000/docs`

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests use an in-memory SQLite database and do not need PostgreSQL or Whisper weights.

## Health check

```bash
curl -i http://localhost:8000/health
```

## Audio upload (SCRUM-55)

`POST /calls` accepts a call recording in MP3 format plus optional call metadata as `multipart/form-data`. The file is stored in `UPLOAD_DIR` as `<call_id>.mp3` and the call is recorded with `processing_status=pending`.

```bash
curl -s -X POST http://localhost:8000/calls \
  -F "audio=@/path/to/call-001.mp3;type=audio/mpeg" \
  -F "caller_number=+905551234567" \
  -F "callee_number=+902321234567" \
  -F "external_call_id=pbx-42" \
  -F "call_started_at=2026-11-20T10:00:00Z" \
  -F "call_ended_at=2026-11-20T10:05:00Z" \
  -F "duration_seconds=300" | python3 -m json.tool
```

| Field | Required | Validation |
|-------|----------|------------|
| `audio` | yes | `.mp3` extension, `audio/mpeg` content type, MP3 header, not empty, at most `MAX_UPLOAD_SIZE_MB` |
| `external_call_id` | no | max 255 characters |
| `caller_number`, `callee_number` | no | max 64 characters |
| `call_started_at`, `call_ended_at` | no | ISO 8601; end must not be before start |
| `duration_seconds` | no | integer ≥ 0 |

Error responses:

| Status | When |
|--------|------|
| `415` | Not an MP3 file (extension, content type or file header) |
| `413` | File larger than `MAX_UPLOAD_SIZE_MB` |
| `422` | Missing or empty file, or invalid metadata |

## Status and transcript retrieval (SCRUM-57)

Used by the AI Evaluation Service to poll a call and fetch its transcript.

```bash
curl -s "http://localhost:8000/calls/${CALL_ID}"             # processing_status: pending / processing / completed / failed
curl -s "http://localhost:8000/calls/${CALL_ID}/transcript"  # latest completed transcript
```

`GET /calls/{id}/transcript` returns `call_id`, `transcription_id`, `transcript_text`, `language`, `created_at` and `updated_at` when the latest transcription is completed.

| Status | When |
|--------|------|
| `200` | Latest transcription is completed |
| `404` | Unknown call, or call is completed but has no transcript text |
| `409` | Transcription is `pending`, `processing` or `failed`; `detail` contains `message`, `call_id`, `processing_status` and `error_message` |
| `422` | Call ID is not a valid UUID |

Example `409` body:

```json
{
  "detail": {
    "message": "Transcription is not ready yet",
    "call_id": "6f1c...",
    "processing_status": "processing",
    "error_message": null
  }
}
```

## Calls and transcriptions (SCRUM-54)

Add a transcription result:

```bash
CALL_ID=<uuid-from-create-response>
curl -s -X POST "http://localhost:8000/calls/${CALL_ID}/transcriptions" \
  -H 'Content-Type: application/json' \
  -d '{"transcript_text": "Merhaba, nasıl yardımcı olabilirim?", "language": "tr"}'
```

Retrieve call with nested transcriptions:

```bash
curl -s "http://localhost:8000/calls/${CALL_ID}"
```

Retrieve a transcription by id:

```bash
curl -s "http://localhost:8000/transcriptions/<transcription-uuid>"
```

## Speech-to-text (SCRUM-56)

`POST /transcribe` accepts a multipart audio upload, runs the configured STT provider, and persists the call + transcription rows (including `processing_status`).

### Providers

| `STT_PROVIDER` | Behavior |
|----------------|----------|
| `local` (default) | **faster-whisper** on CPU; no API key. Default model `tiny` (fast demo). First request downloads model weights. |
| `openai` | OpenAI Whisper API (`OPENAI_API_KEY` required). Optional upgrade for better accuracy. |
| `mock` | Placeholder transcript only. Set explicitly for automated tests/CI — **not** used by default. |

### Verify local transcription (default)

Use any speech recording (WAV, MP3, or FLAC). Example with OpenAI's public JFK test clip:

```bash
curl -L -o /tmp/sample_speech.flac \
  "https://raw.githubusercontent.com/openai/whisper/main/tests/jfk.flac"

# STT_PROVIDER defaults to local; PostgreSQL must be running and migrated
uvicorn app.main:app --host 0.0.0.0 --port 8000

curl -s -X POST http://localhost:8000/transcribe \
  -F "audio=@/tmp/sample_speech.flac;type=audio/flac" \
  -F "caller_number=+905551234567" | python3 -m json.tool
```

Expect:

- `transcription.processing_status` → `completed`
- `transcription.transcript_text` → real words (not a `[mock]` prefix)
- `transcription.language` → detected language when confidence is high enough

For a quick unit smoke test without HTTP or PostgreSQL:

```bash
python3 - <<'PY'
from pathlib import Path
from app.services.stt.factory import get_stt_provider
from app.core.config import Settings

provider = get_stt_provider(Settings(stt_provider="local", local_whisper_model="tiny"))
# replace with any local speech .wav path
result = provider.transcribe(Path("/tmp/sample_speech.flac"))
print(result.text)
PY
```

### Mock provider (tests only)

```bash
export STT_PROVIDER=mock
uvicorn app.main:app --host 0.0.0.0 --port 8000

curl -s -X POST http://localhost:8000/transcribe \
  -F "audio=@/tmp/sample_speech.flac;type=audio/flac" | python3 -m json.tool
```

Expect a `[mock]` transcript string.

### OpenAI Whisper (optional cloud)

```bash
export STT_PROVIDER=openai
export OPENAI_API_KEY=sk-your-key
uvicorn app.main:app --host 0.0.0.0 --port 8000

curl -s -X POST http://localhost:8000/transcribe \
  -F "audio=@/path/to/recording.mp3;type=audio/mpeg" \
  -F "external_call_id=demo-001" | python3 -m json.tool
```

### Provider failure handling

Failures are logged server-side (`STT provider failed for call ...`) and stored on the transcription row:

- `transcription.processing_status` → `failed`
- `transcription.error_message` → provider error text
- `call.processing_status` → `failed`

To verify OpenAI wiring without a key:

```bash
STT_PROVIDER=openai uvicorn app.main:app --port 8000
# POST /transcribe → fails at startup or request with missing OPENAI_API_KEY
```

### Manual transcription quality testing

1. Prepare 2–3 reference recordings (e.g. clear Turkish support call, noisy line, short greeting) with known expected phrases.
2. Run each file through `POST /transcribe` with default `STT_PROVIDER=local` or with `openai` and a valid `OPENAI_API_KEY`.
3. Compare `transcription.transcript_text` to the expected text:
   - Note word errors, missing sentences, and language detection (`language` field when available).
4. Re-fetch via `GET /transcriptions/{id}` or `GET /calls/{call_id}` to confirm persistence.
5. Record findings (file name, expected vs actual, pass/fail) in your sprint notes or Jira comment for SCRUM-56.