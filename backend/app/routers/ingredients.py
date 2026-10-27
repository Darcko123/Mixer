"""Autocompletado de ingredientes (CU-1)."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app import models
from app.db import SessionDep
from app.routers.inventory import ingredient_paths
from app.schemas import IngredientSummary, SearchQuery
from app.search import fuzzy_ids

router = APIRouter(prefix="/ingredients", tags=["ingredients"])


@router.get("")
def search_ingredients(
    params: Annotated[SearchQuery, Query()], session: SessionDep
) -> list[IngredientSummary]:
    """Búsqueda difusa por nombre y alias, con la ruta jerárquica de cada resultado."""
    ids = fuzzy_ids(
        session,
        [
            (models.Ingredient.id, models.Ingredient.name),
            (models.IngredientAlias.ingredient_id, models.IngredientAlias.alias),
        ],
        params.q,
        params.limit,
    )
    rows = {
        i.id: i
        for i in session.scalars(select(models.Ingredient).where(models.Ingredient.id.in_(ids)))
    }
    paths = ingredient_paths(session)
    return [
        IngredientSummary(slug=rows[i].slug, name=rows[i].name, kind=rows[i].kind, path=paths[i])
        for i in ids
    ]
