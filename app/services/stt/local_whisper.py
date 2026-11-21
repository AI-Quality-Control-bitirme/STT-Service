import logging
from functools import lru_cache
from pathlib import Path

from faster_whisper import WhisperModel

from app.services.stt.base import SttProviderError, TranscriptionResult

logger = logging.getLogger(__name__)


@lru_cache(maxsize=4)
def _get_model(model_size: str, device: str, compute_type: str) -> WhisperModel:
    """Load and cache a faster-whisper model (first run downloads weights from Hugging Face)."""
    logger.info(
        "Loading local Whisper model size=%s device=%s compute_type=%s",
        model_size,
        device,
        compute_type,
    )
    return WhisperModel(model_size, device=device, compute_type=compute_type)


class LocalWhisperProvider:
    """On-device STT via faster-whisper (no API key, no speaker diarization)."""

    def __init__(
        self,
        model_size: str = "tiny",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        if not audio_path.is_file():
            raise SttProviderError(f"Audio file not found: {audio_path}")
        try:
            model = _get_model(self._model_size, self._device, self._compute_type)
            segments, info = model.transcribe(str(audio_path))
            text = "".join(segment.text for segment in segments).strip()
        except SttProviderError:
            raise
        except Exception as exc:
            logger.exception("Local Whisper transcription failed for %s", audio_path.name)
            raise SttProviderError(f"Local Whisper transcription failed: {exc}") from exc

        if not text:
            raise SttProviderError(
                "Local Whisper returned an empty transcript "
                "(silence or non-speech audio is expected for some test files)"
            )
        language = info.language if info.language_probability >= 0.5 else None
        logger.info(
            "Local Whisper transcribed %s (%s chars, lang=%s)",
            audio_path.name,
            len(text),
            language,
        )
        return TranscriptionResult(text=text, language=language)