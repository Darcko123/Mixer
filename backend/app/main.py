from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.catalog import Catalog, load_catalog
from app.db import SessionDep, engine
from app.routers import ingredients, inventory, recipes


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    with Session(engine) as session:
        app.state.catalog = load_catalog(session)
    yield


app = FastAPI(title="Mixer API", lifespan=lifespan)
app.include_router(ingredients.router, prefix="/api")
app.include_router(inventory.router, prefix="/api")
app.include_router(recipes.router, prefix="/api")
# Fotos de las recetas (recipe_image.file), versionadas con el catálogo.
app.mount(
    "/api/images",
    StaticFiles(directory=Path(__file__).parents[1] / "data" / "images"),
    name="images",
)


def _summary(catalog: Catalog | None) -> dict[str, int] | None:
    if catalog is None:
        return None
    return {"ingredients": len(catalog.ingredients), "recipes": len(catalog.recipes)}


@app.get("/api/health")
def health(request: Request) -> dict:
    """Liveness y tamaño del catálogo en memoria (`null` si no se ha cargado)."""
    return {"status": "ok", "catalog": _summary(getattr(request.app.state, "catalog", None))}


@app.post("/api/catalog/reload", tags=["catalog"])
def reload_catalog(request: Request, session: SessionDep) -> dict[str, int] | None:
    """Vuelve a leer el catálogo de la BD; lo llama el seed tras escribir cambios."""
    request.app.state.catalog = load_catalog(session)
    return _summary(request.app.state.catalog)
