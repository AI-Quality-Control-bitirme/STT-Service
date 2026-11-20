# STT-Service

Speech-to-text conversion service for the AI Quality Control platform.

## Project structure

```
STT-Service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── api/
│   │   └── routes/
│   │       └── health.py    # Health check endpoint
│   └── core/
│       └── config.py        # Environment configuration (pydantic-settings)
├── .env.example             # Environment variable template
├── requirements.txt         # Python dependencies
└── README.md
```

## Prerequisites

- Python 3.11+

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

   Edit `.env` as needed. Available settings:

   | Variable   | Default       | Description              |
   |------------|---------------|--------------------------|
   | `APP_NAME` | STT Service   | Application display name |
   | `APP_ENV`  | development   | Environment label        |
   | `DEBUG`    | true          | Enable debug mode        |
   | `HOST`     | 0.0.0.0       | Bind host                |
   | `PORT`     | 8000          | Bind port                |

## Startup

Run the development server with Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Or use values from `.env`:

```bash
uvicorn app.main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000} --reload
```

The API is available at `http://localhost:8000`.

## Health check

```bash
curl -i http://localhost:8000/health
```

Expected response: `HTTP/1.1 200 OK` with body `{"status":"ok"}`.

Interactive API docs: `http://localhost:8000/docs`