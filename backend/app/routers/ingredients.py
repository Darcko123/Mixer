"""Autocompletado de ingredientes (CU-1)."""

from typing import Annotated

from fastapi import APIRouter, Query

from app import models
from app.db import CatalogDep, SessionDep
from app.schemas import IngredientSummary, SearchQuery
from app.search import fuzzy_ids

router = APIRouter(prefix="/ingredients", tags=["ingredients"])


@router.get("")
def search_ingredients(
    params: Annotated[SearchQuery, Query()], session: SessionDep, catalog: CatalogDep
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
    return [
        IngredientSummary(
            slug=ingredient.slug,
            name=ingredient.name,
            kind=ingredient.kind,
            path=catalog.paths[i],
        )
        for i in ids
        if (ingredient := catalog.ingredients.get(i))  # aún no recargado tras el seed
    ]
