from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class SttProviderError(Exception):
    """Raised when the speech-to-text provider fails."""


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str | None = None


class SpeechToTextProvider(Protocol):
    def transcribe(self, audio_path: Path) -> TranscriptionResult: ...