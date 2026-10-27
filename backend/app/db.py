import os
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Por defecto apunta al servicio `db` de docker-compose.yml.
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://mixer:mixer@localhost:5432/mixer"
)

engine = create_engine(DATABASE_URL)


def get_session() -> Iterator[Session]:
    """Dependencia de FastAPI: una sesión por petición."""
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
