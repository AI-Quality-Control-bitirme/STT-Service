import logging
from pathlib import Path

from app.services.stt.base import TranscriptionResult, SttProviderError

logger = logging.getLogger(__name__)


class MockSttProvider:
    """Deterministic dev provider; no API key required."""

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        if not audio_path.is_file():
            raise SttProviderError(f"Audio file not found: {audio_path}")
        size = audio_path.stat().st_size
        if size == 0:
            raise SttProviderError("Audio file is empty")
        logger.info("Mock STT transcribing %s (%s bytes)", audio_path.name, size)
        text = (
            f"[mock] Transcription of {audio_path.name} "
            f"({size} bytes). Use default STT_PROVIDER=local or STT_PROVIDER=openai for real STT."
        )
        return TranscriptionResult(text=text, language="mock")