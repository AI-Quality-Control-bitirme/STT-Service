from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.call_repository import CallRepository


def get_call_repository(
    session: Session = Depends(get_db),
) -> CallRepository:
    return CallRepository(session)