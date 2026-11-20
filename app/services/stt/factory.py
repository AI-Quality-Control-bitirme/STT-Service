from app.core.config import Settings, get_settings
from app.services.stt.base import SpeechToTextProvider
from app.services.stt.mock import MockSttProvider
from app.services.stt.openai_whisper import OpenAIWhisperProvider


def get_stt_provider(settings: Settings | None = None) -> SpeechToTextProvider:
    settings = settings or get_settings()
    provider = settings.stt_provider.lower()
    if provider == "mock":
        return MockSttProvider()
    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is required when STT_PROVIDER=openai"
            )
        return OpenAIWhisperProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_whisper_model,
        )
    raise ValueError(f"Unsupported STT_PROVIDER: {settings.stt_provider}")