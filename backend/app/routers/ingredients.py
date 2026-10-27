"""Autocompletado y árbol de ingredientes (CU-1)."""

from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Query

from app import models
from app.catalog import Ingredient
from app.db import CatalogDep, SessionDep
from app.schemas import IngredientNode, IngredientSummary, SearchQuery
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


@router.get("/tree")
def ingredient_tree(catalog: CatalogDep) -> list[IngredientNode]:
    """Jerarquía completa desde el catálogo en memoria, con los hijos ordenados por nombre.

    Un `parent_id` ausente del catálogo deja el nodo como raíz. Se recorre desde las raíces,
    así que un ciclo (que no tiene raíz) no se alcanza y no cuelga la respuesta.
    """
    children: dict[int | None, list[Ingredient]] = defaultdict(list)
    for ingredient in catalog.ingredients.values():
        parent_id = ingredient.parent_id if ingredient.parent_id in catalog.ingredients else None
        children[parent_id].append(ingredient)

    def nodes(parent_id: int | None) -> list[IngredientNode]:
        return [
            IngredientNode(
                slug=ingredient.slug,
                name=ingredient.name,
                kind=ingredient.kind,
                children=nodes(ingredient.id),
            )
            for ingredient in sorted(children[parent_id], key=lambda i: i.name)
        ]

    return nodes(None)
