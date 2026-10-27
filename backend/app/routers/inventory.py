"""Inventario del usuario, "Mi barra" (CU-1)."""

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app import models
from app.catalog import Catalog
from app.db import CatalogDep, SessionDep
from app.schemas import InventoryItem

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _item(
    ingredient: models.Ingredient, row: models.InventoryItem, catalog: Catalog
) -> InventoryItem:
    return InventoryItem(
        slug=ingredient.slug,
        name=ingredient.name,
        kind=ingredient.kind,
        # Sin ruta si el catálogo aún no se recargó tras el seed.
        path=catalog.paths.get(ingredient.id, (ingredient.name,)),
        added_at=row.added_at,
    )


def _ingredient(session: Session, slug: str) -> models.Ingredient:
    ingredient = session.scalar(select(models.Ingredient).where(models.Ingredient.slug == slug))
    if ingredient is None:
        raise HTTPException(404, f"Ingrediente desconocido: {slug}")
    return ingredient


@router.get("")
def list_inventory(session: SessionDep, catalog: CatalogDep) -> list[InventoryItem]:
    """Inventario actual, ordenado por su ruta jerárquica (agrupa por categoría)."""
    rows = session.execute(
        select(models.Ingredient, models.InventoryItem).join(
            models.InventoryItem, models.InventoryItem.ingredient_id == models.Ingredient.id
        )
    )
    return sorted((_item(i, row, catalog) for i, row in rows), key=lambda item: item.path)


@router.put("/{slug}")
def add_to_inventory(slug: str, session: SessionDep, catalog: CatalogDep) -> InventoryItem:
    """Añade un ingrediente; repetirlo no cambia nada (conserva el `added_at` original)."""
    ingredient = _ingredient(session, slug)
    if ingredient.kind == "category":
        raise HTTPException(422, f"{ingredient.name} es una categoría, no un ingrediente")
    session.execute(
        insert(models.InventoryItem)
        .values(ingredient_id=ingredient.id)
        .on_conflict_do_nothing(index_elements=["ingredient_id"])
    )
    session.commit()
    row = session.get_one(models.InventoryItem, ingredient.id)
    return _item(ingredient, row, catalog)


@router.delete("/{slug}", status_code=204)
def remove_from_inventory(slug: str, session: SessionDep) -> Response:
    """Quita un ingrediente; quitar uno que no está en el inventario también da `204`."""
    ingredient = _ingredient(session, slug)
    session.execute(
        delete(models.InventoryItem).where(models.InventoryItem.ingredient_id == ingredient.id)
    )
    session.commit()
    return Response(status_code=204)
