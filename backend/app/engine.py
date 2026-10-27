"""Motor de coincidencias (§5.2–5.4): cobertura del inventario, evaluación y ranking de recetas.

Funciones puras sobre un `Catalog` ya construido: no consultan la BD. `evaluate()` acepta la
cobertura precalculada para evaluar muchas recetas sin repetir el trabajo (ranking y compras).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from app.catalog import Catalog, Recipe, RequirementGroup

Status = Literal["have", "have_equivalent", "substitute", "missing"]


@dataclass(frozen=True, slots=True)
class GroupEvaluation:
    """Estado de un grupo de requisitos (`alt_group` o un ingrediente suelto).

    `matched_ingredient_id` es el requisito que se satisface; `substitute_id` solo se rellena
    en `substitute`. `covered_by` es el artículo del inventario que lo cubre (en `have` coincide
    con el requisito, o con el básico asumido).
    """

    group: RequirementGroup
    status: Status
    matched_ingredient_id: int | None = None
    substitute_id: int | None = None
    covered_by: int | None = None


@dataclass(frozen=True, slots=True)
class RecipeEvaluation:
    """Resultado de evaluar los requisitos de una receta frente al inventario."""

    recipe: Recipe
    groups: tuple[GroupEvaluation, ...]

    @property
    def required_count(self) -> int:
        return len(self.groups)

    @property
    def missing_count(self) -> int:
        return sum(1 for group in self.groups if group.status == "missing")

    @property
    def substitute_count(self) -> int:
        return sum(1 for group in self.groups if group.status == "substitute")

    @property
    def can_make(self) -> bool:
        """Preparable aunque se usen sustitutos: solo los `missing` lo impiden (§5.4)."""
        return self.missing_count == 0


def coverage(catalog: Catalog, inventory: Iterable[int]) -> frozenset[int]:
    """Cobertura del inventario (§5.2): básicos + ancestros de cada artículo."""
    covered = set(catalog.staples)
    for ingredient_id in inventory:
        covered.update(catalog.ancestors_or_self.get(ingredient_id, ()))
    return frozenset(covered)


def _coverer(catalog: Catalog, target: int, inventory: frozenset[int]) -> int | None:
    """Artículo del inventario (o básico) que satisface `target`; el menor id si hay varios."""
    if target in inventory or target in catalog.staples:
        return target
    coverers = [
        ingredient_id
        for ingredient_id in inventory
        if target in catalog.ancestors_or_self.get(ingredient_id, ())
    ]
    return min(coverers) if coverers else None


def _match_group(
    catalog: Catalog,
    group: RequirementGroup,
    inventory: frozenset[int],
    covered: frozenset[int],
    allow_substitutes: bool,
) -> GroupEvaluation:
    # Preferencia: lo que el usuario tiene exactamente, luego los básicos asumidos, luego la
    # herencia y, por último, un sustituto (mejor calidad primero).
    for ingredient_id in group.ingredient_ids:
        if ingredient_id in inventory:
            return GroupEvaluation(
                group, "have", matched_ingredient_id=ingredient_id, covered_by=ingredient_id
            )

    for ingredient_id in group.ingredient_ids:
        if ingredient_id in catalog.staples:
            return GroupEvaluation(
                group, "have", matched_ingredient_id=ingredient_id, covered_by=ingredient_id
            )

    for ingredient_id in group.ingredient_ids:
        if ingredient_id in covered:
            return GroupEvaluation(
                group,
                "have_equivalent",
                matched_ingredient_id=ingredient_id,
                covered_by=_coverer(catalog, ingredient_id, inventory),
            )

    if allow_substitutes:
        for ingredient_id in group.ingredient_ids:
            candidates = sorted(
                catalog.substitutes.get(ingredient_id, ()), key=lambda pair: (-pair[1], pair[0])
            )
            for substitute_id, _quality in candidates:
                if substitute_id in covered:
                    return GroupEvaluation(
                        group,
                        "substitute",
                        matched_ingredient_id=ingredient_id,
                        substitute_id=substitute_id,
                        covered_by=_coverer(catalog, substitute_id, inventory),
                    )

    return GroupEvaluation(group, "missing")


def evaluate(
    catalog: Catalog,
    recipe: Recipe,
    inventory: Iterable[int],
    *,
    allow_substitutes: bool = True,
    covered: frozenset[int] | None = None,
) -> RecipeEvaluation:
    """Evalúa los grupos `required` de una receta (§5.3).

    `covered` permite reutilizar `coverage()` entre recetas; si se omite se calcula aquí.
    Con `allow_substitutes=False`, un `substitute` se trata como `missing` (§5.4).
    """
    items = frozenset(inventory)
    if covered is None:
        covered = coverage(catalog, items)
    return RecipeEvaluation(
        recipe=recipe,
        groups=tuple(
            _match_group(catalog, group, items, covered, allow_substitutes)
            for group in recipe.required_groups
        ),
    )


@dataclass(frozen=True, slots=True)
class Matches:
    """*Puedo preparar* (CU-2) y *Casi listos* (CU-3), ya ordenados (§5.4)."""

    can_make: tuple[RecipeEvaluation, ...]
    almost: tuple[RecipeEvaluation, ...]


def rank(
    catalog: Catalog,
    inventory: Iterable[int],
    *,
    max_missing: int = 2,
    allow_substitutes: bool = True,
) -> Matches:
    """Clasifica todas las recetas en *Puedo preparar* y *Casi listos* (§5.4).

    El primer elemento de `almost` es "la bebida más cercana". El slug desempata al final para
    que el orden sea determinista.
    """
    items = frozenset(inventory)
    covered = coverage(catalog, items)
    can_make: list[RecipeEvaluation] = []
    almost: list[RecipeEvaluation] = []
    for recipe in catalog.recipes.values():
        result = evaluate(
            catalog, recipe, items, allow_substitutes=allow_substitutes, covered=covered
        )
        if result.can_make:
            can_make.append(result)
        elif result.missing_count <= max_missing:
            almost.append(result)

    can_make.sort(key=lambda r: (r.substitute_count, -r.recipe.popularity, r.recipe.slug))
    # Primero cuántas compras faltan; la cobertura relativa solo desempata (§5.4).
    almost.sort(
        key=lambda r: (
            r.missing_count,
            r.substitute_count,
            -(r.required_count - r.missing_count) / r.required_count,
            -r.recipe.popularity,
            r.recipe.slug,
        )
    )
    return Matches(can_make=tuple(can_make), almost=tuple(almost))
