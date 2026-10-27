import os
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.catalog import Catalog

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


def get_catalog(request: Request) -> Catalog:
    """Catálogo en memoria: lo carga el *lifespan* y lo reemplaza `POST /catalog/reload`."""
    return request.app.state.catalog


CatalogDep = Annotated[Catalog, Depends(get_catalog)]
