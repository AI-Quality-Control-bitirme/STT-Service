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
│   │   └── stt/             # mock + OpenAI Whisper providers
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

3. Copy environment configuration:

   ```bash
   cp .env.example .env
   ```

   | Variable        | Default                                                          | Description              |
   |-----------------|--------------------------------------------------------------------|--------------------------|
   | `APP_NAME`      | STT Service                                                        | Application display name |
   | `APP_ENV`       | development                                                        | Environment label        |
   | `DEBUG`         | true                                                               | Enable debug mode        |
   | `HOST`          | 0.0.0.0                                                            | Bind host                |
   | `PORT`          | 8000                                                               | Bind port                |
   | `DATABASE_URL`  | postgresql+psycopg://stt_user:stt_pass@localhost:5432/stt_db     | PostgreSQL connection    |
   | `STT_PROVIDER`  | mock                                                               | `mock` or `openai`       |
   | `OPENAI_API_KEY`| (unset)                                                            | Required for OpenAI STT  |
   | `UPLOAD_DIR`    | uploads                                                            | Stored audio files       |

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

## Startup

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs: `http://localhost:8000/docs`

## Health check

```bash
curl -i http://localhost:8000/health
```

## Calls and transcriptions (SCRUM-54)

Create a call (stores audio reference + metadata):

```bash
curl -s -X POST http://localhost:8000/calls \
  -H 'Content-Type: application/json' \
  -d '{"audio_file_ref": "s3://bucket/recordings/call-001.wav", "caller_number": "+905551234567"}'
```

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
| `mock` (default) | No API key; returns a deterministic placeholder transcript. Use for local smoke tests and CI. |
| `openai` | Calls OpenAI Whisper (`OPENAI_API_KEY` required). |

### Smoke test (mock, no API key)

```bash
# Create a tiny sample file (replace with a real .wav/.mp3 for quality testing)
printf 'RIFF....' > /tmp/sample.wav

curl -s -X POST http://localhost:8000/transcribe \
  -F "audio=@/tmp/sample.wav;type=audio/wav" \
  -F "caller_number=+905551234567" | python3 -m json.tool
```

Expect `call.processing_status` and `transcription.processing_status` of `completed`, with a `[mock]` transcript string.

### Real transcription (OpenAI Whisper)

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

To verify locally without calling OpenAI:

```bash
STT_PROVIDER=openai uvicorn app.main:app --port 8000
# POST /transcribe → fails with missing OPENAI_API_KEY; check logs and JSON error_message
```

### Manual transcription quality testing

1. Prepare 2–3 reference recordings (e.g. clear Turkish support call, noisy line, short greeting) with known expected phrases.
2. Run each file through `POST /transcribe` with `STT_PROVIDER=openai` and a valid `OPENAI_API_KEY`.
3. Compare `transcription.transcript_text` to the expected text:
   - Note word errors, missing sentences, and language detection (`language` field when available).
4. Re-fetch via `GET /transcriptions/{id}` or `GET /calls/{call_id}` to confirm persistence.
5. Record findings (file name, expected vs actual, pass/fail) in your sprint notes or Jira comment for SCRUM-56.