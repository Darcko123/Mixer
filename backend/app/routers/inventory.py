"""Inventario del usuario, "Mi barra" (CU-1)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app import models
from app.db import get_session
from app.schemas import InventoryItem

router = APIRouter(prefix="/inventory", tags=["inventory"])

SessionDep = Annotated[Session, Depends(get_session)]


def _paths(session: Session) -> dict[int, list[str]]:
    """Nombres desde la raíz hasta cada ingrediente."""
    # ponytail: lee toda la taxonomía (~300 filas) por petición; usar el catálogo en memoria
    # cuando la API lo cargue al arrancar (F4.T5).
    rows = {i.id: i for i in session.scalars(select(models.Ingredient))}
    paths: dict[int, list[str]] = {}
    for ingredient_id in rows:
        chain: list[str] = []
        current = rows.get(ingredient_id)
        while current is not None and len(chain) < len(rows):  # tope por si hubiera un ciclo
            chain.append(current.name)
            current = rows.get(current.parent_id) if current.parent_id is not None else None
        paths[ingredient_id] = chain[::-1]
    return paths


def _item(
    ingredient: models.Ingredient, row: models.InventoryItem, paths: dict[int, list[str]]
) -> InventoryItem:
    return InventoryItem(
        slug=ingredient.slug,
        name=ingredient.name,
        kind=ingredient.kind,
        path=paths[ingredient.id],
        added_at=row.added_at,
    )


def _ingredient(session: Session, slug: str) -> models.Ingredient:
    ingredient = session.scalar(select(models.Ingredient).where(models.Ingredient.slug == slug))
    if ingredient is None:
        raise HTTPException(404, f"Ingrediente desconocido: {slug}")
    return ingredient


@router.get("")
def list_inventory(session: SessionDep) -> list[InventoryItem]:
    """Inventario actual, ordenado por su ruta jerárquica (agrupa por categoría)."""
    paths = _paths(session)
    rows = session.execute(
        select(models.Ingredient, models.InventoryItem).join(
            models.InventoryItem, models.InventoryItem.ingredient_id == models.Ingredient.id
        )
    )
    return sorted((_item(i, row, paths) for i, row in rows), key=lambda item: item.path)


@router.put("/{slug}")
def add_to_inventory(slug: str, session: SessionDep) -> InventoryItem:
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
    return _item(ingredient, row, _paths(session))


@router.delete("/{slug}", status_code=204)
def remove_from_inventory(slug: str, session: SessionDep) -> Response:
    """Quita un ingrediente; quitar uno que no está en el inventario también da `204`."""
    ingredient = _ingredient(session, slug)
    session.execute(
        delete(models.InventoryItem).where(models.InventoryItem.ingredient_id == ingredient.id)
    )
    session.commit()
    return Response(status_code=204)
