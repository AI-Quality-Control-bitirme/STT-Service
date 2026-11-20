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
│   │       └── calls.py     # Call + transcription CRUD
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