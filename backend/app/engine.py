"""Motor de coincidencias (§5.2–5.5): cobertura, evaluación, ranking y recomendación de compras.

Funciones puras sobre un `Catalog` ya construido: no consultan la BD. `evaluate()` acepta la
cobertura precalculada para evaluar muchas recetas sin repetir el trabajo (ranking y compras).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from itertools import combinations
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


@dataclass(frozen=True, slots=True)
class Purchase:
    """Compra sugerida (§5.5), relativa al inventario más las compras anteriores del plan.

    `unlocks` son las recetas que pasan a preparables; `improves`, las que se acercan sin
    completarse. Ambas ordenadas por popularidad descendente y slug.
    """

    ingredient_id: int
    unlocks: tuple[Recipe, ...]
    improves: tuple[Recipe, ...]


# Grupos `missing` de cada receta como bits: receta → máscara de grupos cubiertos.
_Masks = dict[int, int]


def _advance(state: _Masks, hits: _Masks) -> _Masks:
    """Recetas cuya máscara cambia al añadir una compra que cubre `hits`."""
    changes: _Masks = {}
    for recipe_id, bits in hits.items():
        before = state.get(recipe_id, 0)
        if (after := before | bits) != before:
            changes[recipe_id] = after
    return changes


def _gain(full: _Masks, changes: _Masks) -> tuple[int, float]:
    """(recetas completadas, progreso parcial Σ 1 / (m_restante + 1)) de un cambio."""
    remaining = [(full[recipe_id] & ~mask).bit_count() for recipe_id, mask in changes.items()]
    return sum(1 for m in remaining if m == 0), sum(1 / (m + 1) for m in remaining if m)


def _score(gain: tuple[int, float]) -> float:
    completed, progress = gain
    return 10 * completed + progress


def _merge(a: _Masks, b: _Masks) -> _Masks:
    merged = dict(a)
    for recipe_id, bits in b.items():
        merged[recipe_id] = merged.get(recipe_id, 0) | bits
    return merged


def suggest_purchases(
    catalog: Catalog,
    inventory: Iterable[int],
    k: int = 1,
    *,
    allow_substitutes: bool = True,
) -> tuple[Purchase, ...]:
    """Recomienda hasta `k` compras, en el orden en que conviene hacerlas (§5.5).

    Candidatos: los ingredientes de los grupos `missing` de las recetas con `m ≤ k`. Comprar
    `x` cubre `ancestors_or_self[x]`, así que un candidato puede satisfacer requisitos de
    distintos niveles (o como sustituto). k = 1 ordena por recetas desbloqueadas y desempata
    por progreso parcial; k = 2 evalúa todas las parejas y k ≥ 3 usa el greedy.
    """
    items = frozenset(inventory)
    covered = coverage(catalog, items)

    full: _Masks = {}
    by_target: dict[int, list[tuple[int, int]]] = {}
    candidates: set[int] = set()
    for recipe in catalog.recipes.values():
        result = evaluate(
            catalog, recipe, items, allow_substitutes=allow_substitutes, covered=covered
        )
        missing = [g.group for g in result.groups if g.status == "missing"]
        if not missing:
            continue
        full[recipe.id] = (1 << len(missing)) - 1
        for bit, group in enumerate(missing):
            targets = set(group.ingredient_ids)
            if allow_substitutes:
                for ingredient_id in group.ingredient_ids:
                    targets.update(s for s, _q in catalog.substitutes.get(ingredient_id, ()))
            for target in targets:
                by_target.setdefault(target, []).append((recipe.id, 1 << bit))
            if len(missing) <= k:
                candidates.update(group.ingredient_ids)

    hits: dict[int, _Masks] = {}
    for candidate in candidates:
        masks: _Masks = {}
        for ingredient_id in catalog.ancestors_or_self[candidate]:
            for recipe_id, bit in by_target.get(ingredient_id, ()):
                masks[recipe_id] = masks.get(recipe_id, 0) | bit
        hits[candidate] = masks

    # Orden por slug: con `max()` gana el primero, así los empates son deterministas.
    pool = sorted(candidates, key=lambda x: catalog.ingredients[x].slug)
    if k == 2 and len(pool) >= 2:
        # ponytail: fusiona dicts por pareja (O(candidatos² · recetas)); si pesa con catálogos
        # grandes, sumar los valores individuales y corregir solo las recetas compartidas.
        pair = max(
            combinations(pool, 2),
            key=lambda p: _score(_gain(full, _advance({}, _merge(hits[p[0]], hits[p[1]])))),
        )
        chosen = sorted(
            pair, key=lambda x: _score(_gain(full, _advance({}, hits[x]))), reverse=True
        )
    else:
        # k = 1: orden lexicográfico (desbloqueos, progreso); k ≥ 3: greedy con 10·c + p.
        key = (lambda g: g) if k == 1 else _score
        state: _Masks = {}
        chosen = []
        for _ in range(max(k, 0)):
            if not pool:
                break
            best = max(pool, key=lambda x: key(_gain(full, _advance(state, hits[x]))))
            chosen.append(best)
            pool.remove(best)
            state.update(_advance(state, hits[best]))

    def by_popularity(recipe_ids: Iterable[int]) -> tuple[Recipe, ...]:
        recipes = (catalog.recipes[recipe_id] for recipe_id in recipe_ids)
        return tuple(sorted(recipes, key=lambda r: (-r.popularity, r.slug)))

    state = {}
    purchases: list[Purchase] = []
    for ingredient_id in chosen:
        changes = _advance(state, hits[ingredient_id])
        if not changes:  # no aporta nada sobre las compras anteriores
            continue
        state.update(changes)
        purchases.append(
            Purchase(
                ingredient_id,
                unlocks=by_popularity(r for r, mask in changes.items() if mask == full[r]),
                improves=by_popularity(r for r, mask in changes.items() if mask != full[r]),
            )
        )
    return tuple(purchases)
