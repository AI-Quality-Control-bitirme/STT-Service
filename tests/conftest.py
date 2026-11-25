import sys
import types
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Tests must not download Whisper weights; the provider module imports faster_whisper at load time.
if "faster_whisper" not in sys.modules:
    _fake_whisper = types.ModuleType("faster_whisper")
    _fake_whisper.WhisperModel = object
    sys.modules["faster_whisper"] = _fake_whisper

from app.api.deps import get_call_upload_service  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Call, Transcription  # noqa: E402,F401
from app.services.call_upload_service import CallUploadService  # noqa: E402


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def upload_dir(tmp_path: Path) -> Path:
    return tmp_path / "uploads"


@pytest.fixture
def client(db_session: Session, upload_dir: Path) -> Generator[TestClient, None, None]:
    settings = Settings(upload_dir=str(upload_dir), max_upload_size_mb=1)
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_call_upload_service] = lambda: CallUploadService(
        db_session, settings
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
