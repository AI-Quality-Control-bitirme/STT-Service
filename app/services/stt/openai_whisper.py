import logging
from pathlib import Path

from openai import APIConnectionError, APIStatusError, OpenAI

from app.services.stt.base import TranscriptionResult, SttProviderError

logger = logging.getLogger(__name__)


class OpenAIWhisperProvider:
    def __init__(self, api_key: str, model: str = "whisper-1") -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        if not audio_path.is_file():
            raise SttProviderError(f"Audio file not found: {audio_path}")
        try:
            with audio_path.open("rb") as audio_file:
                response = self._client.audio.transcriptions.create(
                    model=self._model,
                    file=audio_file,
                )
        except APIStatusError as exc:
            logger.error(
                "OpenAI Whisper API status error: status=%s message=%s",
                exc.status_code,
                exc.message,
            )
            raise SttProviderError(f"OpenAI Whisper API error: {exc.message}") from exc
        except APIConnectionError as exc:
            logger.error("OpenAI Whisper connection error: %s", exc)
            raise SttProviderError("Could not connect to OpenAI Whisper API") from exc
        except Exception as exc:
            logger.exception("Unexpected OpenAI Whisper failure")
            raise SttProviderError(f"Transcription failed: {exc}") from exc

        text = (response.text or "").strip()
        if not text:
            raise SttProviderError("OpenAI Whisper returned an empty transcript")
        logger.info("OpenAI Whisper transcribed %s (%s chars)", audio_path.name, len(text))
        return TranscriptionResult(text=text, language=None)