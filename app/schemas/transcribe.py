from pydantic import BaseModel, ConfigDict

from app.schemas.call import CallRead
from app.schemas.transcription import TranscriptionRead


class TranscribeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    call: CallRead
    transcription: TranscriptionRead