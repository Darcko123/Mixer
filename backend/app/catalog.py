"""Catálogo en memoria que consume el motor de coincidencias (§5.1).

`load_catalog(session)` lee la BD y `build_catalog(...)` monta las estructuras a partir de
datos ya cargados (útil para fixtures sin BD). El motor recibe este catálogo y no consulta
la BD: así las coincidencias se calculan en milisegundos y se prueban sin PostgreSQL.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models


@dataclass(frozen=True, slots=True)
class Ingredient:
    id: int
    slug: str
    name: str
    kind: str
    parent_id: int | None = None
    is_staple: bool = False


@dataclass(frozen=True, slots=True)
class Substitute:
    """`substitute_id` puede reemplazar a `ingredient_id` (relación dirigida)."""

    ingredient_id: int
    substitute_id: int
    quality: int


@dataclass(frozen=True, slots=True)
class RecipeIngredient:
    recipe_id: int
    ingredient_id: int
    position: int
    role: str = "required"
    alt_group: int | None = None
    amount: Decimal | None = None
    unit: str | None = None
    amount_ml: int | None = None


@dataclass(frozen=True, slots=True)
class RecipeMeta:
    """Datos de cabecera de una receta; sus ingredientes van aparte en `build_catalog`."""

    id: int
    slug: str
    name: str
    popularity: int = 0


@dataclass(frozen=True, slots=True)
class RequirementGroup:
    """Requisitos alternativos: basta con uno de `ingredient_ids`.

    `alt_group` es el valor del YAML; `None` identifica un grupo de un solo ingrediente.
    """

    alt_group: int | None
    ingredient_ids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class Recipe:
    id: int
    slug: str
    name: str
    popularity: int
    ingredients: tuple[RecipeIngredient, ...]
    required_groups: tuple[RequirementGroup, ...]


@dataclass(slots=True)
class Catalog:
    ingredients: dict[int, Ingredient]
    ingredients_by_slug: dict[str, Ingredient]
    # Ídem que tener el nodo: sus ancestros y él mismo (la cobertura se calcula con esto).
    ancestors_or_self: dict[int, frozenset[int]]
    # Requerido → {(sustituto, quality)}.
    substitutes: dict[int, frozenset[tuple[int, int]]]
    staples: frozenset[int]
    recipes: dict[int, Recipe]
    recipes_by_slug: dict[str, Recipe]


def _ancestors_or_self(ingredient_id: int, ingredients: dict[int, Ingredient]) -> frozenset[int]:
    """Nodo y sus ancestros; termina aunque la jerarquía tuviera un ciclo."""
    chain: list[int] = []
    current: int | None = ingredient_id
    while current is not None and current not in chain:
        chain.append(current)
        parent = ingredients.get(current)
        current = parent.parent_id if parent is not None else None
    return frozenset(chain)


def _required_groups(rows: Iterable[RecipeIngredient]) -> tuple[RequirementGroup, ...]:
    """Agrupa los `required` por `alt_group` y descarta `optional` y `garnish`."""
    groups: list[list[int]] = []
    keys: list[int | None] = []
    by_alt_group: dict[int, int] = {}
    for row in sorted(rows, key=lambda r: r.position):
        if row.role != "required":
            continue
        if row.alt_group is None:
            groups.append([row.ingredient_id])
            keys.append(None)
        elif row.alt_group in by_alt_group:
            groups[by_alt_group[row.alt_group]].append(row.ingredient_id)
        else:
            by_alt_group[row.alt_group] = len(groups)
            groups.append([row.ingredient_id])
            keys.append(row.alt_group)
    return tuple(
        RequirementGroup(keys[i], tuple(ingredient_ids)) for i, ingredient_ids in enumerate(groups)
    )


def build_catalog(
    ingredients: Iterable[Ingredient],
    substitutes: Iterable[Substitute],
    recipes: Iterable[RecipeMeta],
    recipe_ingredients: Iterable[RecipeIngredient],
) -> Catalog:
    """Construye las estructuras de §5.1 a partir de filas ya cargadas."""
    by_id = {ingredient.id: ingredient for ingredient in ingredients}
    by_slug = {ingredient.slug: ingredient for ingredient in by_id.values()}

    substitutes_by_required: dict[int, set[tuple[int, int]]] = {}
    for substitute in substitutes:
        substitutes_by_required.setdefault(substitute.ingredient_id, set()).add(
            (substitute.substitute_id, substitute.quality)
        )

    rows_by_recipe: dict[int, list[RecipeIngredient]] = {}
    for row in recipe_ingredients:
        rows_by_recipe.setdefault(row.recipe_id, []).append(row)

    recipes_by_id: dict[int, Recipe] = {}
    for meta in sorted(recipes, key=lambda r: r.id):
        rows = tuple(sorted(rows_by_recipe.get(meta.id, ()), key=lambda r: r.position))
        recipes_by_id[meta.id] = Recipe(
            id=meta.id,
            slug=meta.slug,
            name=meta.name,
            popularity=meta.popularity,
            ingredients=rows,
            required_groups=_required_groups(rows),
        )

    return Catalog(
        ingredients=by_id,
        ingredients_by_slug=by_slug,
        ancestors_or_self={
            ingredient_id: _ancestors_or_self(ingredient_id, by_id) for ingredient_id in by_id
        },
        substitutes={
            required: frozenset(pairs) for required, pairs in substitutes_by_required.items()
        },
        staples=frozenset(i.id for i in by_id.values() if i.is_staple),
        recipes=recipes_by_id,
        recipes_by_slug={recipe.slug: recipe for recipe in recipes_by_id.values()},
    )


def load_catalog(session: Session) -> Catalog:
    """Lee el catálogo completo de la BD y construye las estructuras en memoria."""
    ingredients = [
        Ingredient(
            id=row.id,
            slug=row.slug,
            name=row.name,
            kind=row.kind,
            parent_id=row.parent_id,
            is_staple=row.is_staple,
        )
        for row in session.scalars(select(models.Ingredient))
    ]
    substitutes = [
        Substitute(
            ingredient_id=row.ingredient_id,
            substitute_id=row.substitute_id,
            quality=row.quality,
        )
        for row in session.scalars(select(models.IngredientSubstitute))
    ]
    recipes = [
        RecipeMeta(id=row.id, slug=row.slug, name=row.name, popularity=row.popularity)
        for row in session.scalars(select(models.Recipe))
    ]
    recipe_ingredients = [
        RecipeIngredient(
            recipe_id=row.recipe_id,
            ingredient_id=row.ingredient_id,
            position=row.position,
            role=row.role,
            alt_group=row.alt_group,
            amount=row.amount,
            unit=row.unit,
            amount_ml=row.amount_ml,
        )
        for row in session.scalars(select(models.RecipeIngredient))
    ]
    return build_catalog(ingredients, substitutes, recipes, recipe_ingredients)
