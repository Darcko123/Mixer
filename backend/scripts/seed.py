"""Carga el catálogo YAML de data/ en la BD: `python -m scripts.seed`.

Valida todo antes de escribir y sincroniza en una sola transacción tocando solo las filas
que cambian: repetirlo sin cambios en los YAML no modifica nada. Nunca escribe en
inventory_item; si un ingrediente del inventario desaparece del catálogo, aborta.
La API carga el catálogo al arrancar: reiniciarla tras el seed.
"""

import sys
import unicodedata
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple

import yaml
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import engine
from app.models import (
    Ingredient,
    IngredientAlias,
    IngredientSubstitute,
    InventoryItem,
    Recipe,
    RecipeAlias,
    RecipeIngredient,
)
from app.units import UNITS, to_ml

DATA_DIR = Path(__file__).parents[1] / "data"

INGREDIENT_KEYS = {"slug", "name", "kind", "parent", "aliases", "is_staple", "abv"}
SUBSTITUTE_KEYS = {"ingredient", "substitute", "quality", "note"}
RECIPE_KEYS = {
    "slug",
    "name",
    "aliases",
    "method",
    "glass",
    "source",
    "popularity",
    "ingredients",
    "garnish_text",
    "instructions",
}
RECIPE_INGREDIENT_KEYS = {"ingredient", "amount", "unit", "role", "alt_group"}
KINDS = {"category", "generic", "brand"}
ROLES = {"required", "optional", "garnish"}


class CatalogError(Exception):
    def __init__(self, errors: list[str]):
        super().__init__("\n".join(errors))


class Catalog(NamedTuple):
    ingredients: dict[str, dict]
    substitutes: list[dict]
    recipes: dict[str, dict]


def normalize(text: str) -> str:
    """Equivalente en Python de immutable_unaccent(lower()) de la BD."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _read(path: Path, errors: list[str], where: str):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        errors.append(f"{where}: no se puede leer: {e}")


def _check_keys(errors, where, item, allowed, required) -> bool:
    if not isinstance(item, dict):
        errors.append(f"{where}: se esperaba un mapeo y hay {item!r}")
        return False
    # Una coma sin comillas dentro de {…} parte el valor en una clave nueva.
    if extra := item.keys() - allowed:
        errors.append(f"{where}: claves desconocidas {sorted(map(str, extra))}")
    if missing := required - item.keys():
        errors.append(f"{where}: faltan claves {sorted(missing)}")
    return not missing


def _unique_names(errors, seen: dict[str, str], where, names) -> None:
    for name in names:
        key = normalize(str(name))
        if key in seen:
            errors.append(f"{where}: '{name}' repite un nombre o alias de {seen[key]}")
        seen[key] = where


def _ancestors_or_self(ingredients: dict[str, dict], slug: str) -> list[str]:
    """Cadena slug → padre → … ; se detiene al repetir un nodo (ciclo)."""
    chain = []
    while slug in ingredients and slug not in chain:
        chain.append(slug)
        slug = ingredients[slug].get("parent")
    return chain


def load_catalog(data_dir: Path = DATA_DIR) -> Catalog:
    """Lee y valida los YAML; lanza CatalogError con todos los problemas (archivo y causa)."""
    errors: list[str] = []
    where = "ingredients.yaml"
    taxonomy = _read(data_dir / "ingredients.yaml", errors, where)
    if not _check_keys(errors, where, taxonomy, {"ingredients", "substitutes"}, {"ingredients"}):
        taxonomy = {}

    ingredients: dict[str, dict] = {}
    names: dict[str, str] = {}
    for n, item in enumerate(taxonomy.get("ingredients") or [], 1):
        if not _check_keys(
            errors, f"{where}: ingrediente #{n}", item, INGREDIENT_KEYS, {"slug", "name", "kind"}
        ):
            continue
        slug = item["slug"]
        w = f"{where}: {slug}"
        if slug in ingredients:
            errors.append(f"{w}: slug repetido")
            continue
        ingredients[slug] = item
        if item["kind"] not in KINDS:
            errors.append(f"{w}: kind '{item['kind']}' no es uno de {sorted(KINDS)}")
        _unique_names(errors, names, w, [item["name"], *(item.get("aliases") or [])])

    for slug, item in ingredients.items():
        parent = item.get("parent")
        if parent is not None and parent not in ingredients:
            errors.append(f"{where}: {slug}: el padre '{parent}' no existe")
        chain = _ancestors_or_self(ingredients, slug)
        # Se reporta una vez por ciclo, desde su slug menor.
        if ingredients[chain[-1]].get("parent") == slug == min(chain):
            errors.append(f"{where}: ciclo en la jerarquía: {' → '.join([*chain, slug])}")

    pairs = set()
    for n, sub in enumerate(taxonomy.get("substitutes") or [], 1):
        if not _check_keys(
            errors,
            f"{where}: sustituto #{n}",
            sub,
            SUBSTITUTE_KEYS,
            {"ingredient", "substitute", "quality"},
        ):
            continue
        required, substitute = sub["ingredient"], sub["substitute"]
        w = f"{where}: sustituto {required} ← {substitute}"
        if missing := [s for s in (required, substitute) if s not in ingredients]:
            errors.append(f"{w}: no existe {missing}")
        elif required in _ancestors_or_self(ingredients, substitute):
            errors.append(f"{w}: el sustituto es el mismo nodo o un descendiente")
        if (required, substitute) in pairs:
            errors.append(f"{w}: repetido")
        pairs.add((required, substitute))
        if sub["quality"] not in (1, 2, 3):
            errors.append(f"{w}: quality debe ser 1, 2 o 3")

    recipes: dict[str, dict] = {}
    names = {}
    for path in sorted((data_dir / "recipes").glob("*.yaml")):
        where = str(path.relative_to(data_dir))
        recipe = _read(path, errors, where)
        if not _check_keys(errors, where, recipe, RECIPE_KEYS, {"slug", "name", "ingredients"}):
            continue
        if recipe["slug"] in recipes:
            errors.append(f"{where}: slug '{recipe['slug']}' repetido")
            continue
        recipes[recipe["slug"]] = recipe
        _unique_names(errors, names, where, [recipe["name"], *(recipe.get("aliases") or [])])
        if not isinstance(recipe["ingredients"], list):
            errors.append(f"{where}: ingredients debe ser una lista")
            recipe["ingredients"] = []

        used = set()
        for n, row in enumerate(recipe["ingredients"], 1):
            w = f"{where}: ingrediente #{n}"
            if not _check_keys(errors, w, row, RECIPE_INGREDIENT_KEYS, {"ingredient"}):
                continue
            slug, amount, unit = row["ingredient"], row.get("amount"), row.get("unit")
            w = f"{where}: {slug}"
            kind = ingredients.get(slug, {}).get("kind")
            if kind is None:
                errors.append(f"{w}: el ingrediente no existe")
            elif kind != "generic":
                errors.append(f"{w}: es {kind}; las recetas citan el genérico")
            if slug in used:
                errors.append(f"{w}: repetido en la receta")
            used.add(slug)
            if row.get("role", "required") not in ROLES:
                errors.append(f"{w}: role '{row['role']}' no es uno de {sorted(ROLES)}")
            if (amount is None) != (unit is None):
                errors.append(f"{w}: amount y unit van juntos o ninguno")
            elif unit is not None:
                if unit not in UNITS:
                    errors.append(f"{w}: unidad desconocida '{unit}'")
                if isinstance(amount, bool) or not isinstance(amount, int | float) or amount <= 0:
                    errors.append(f"{w}: cantidad inválida {amount!r}")
                elif unit == "ml" and amount % 1:
                    errors.append(f"{w}: {amount} ml no es entero")
        if not any(
            isinstance(row, dict) and row.get("role", "required") == "required"
            for row in recipe["ingredients"]
        ):
            errors.append(f"{where}: ningún ingrediente required")

    if errors:
        raise CatalogError(errors)
    return Catalog(ingredients, taxonomy.get("substitutes") or [], recipes)


def _sync(session: Session, model, key: tuple[str, ...], rows: dict, delete=True) -> int:
    """Deja la tabla de `model` igual a `rows` ({clave: valores}) tocando solo lo que cambia.

    Devuelve el número de filas insertadas, actualizadas o borradas.
    """
    existing = {tuple(getattr(o, c) for c in key): o for o in session.scalars(select(model))}
    changes = 0
    if delete:
        for k in existing.keys() - rows.keys():
            session.delete(existing.pop(k))
            changes += 1
        # Borrar antes de insertar: un alias puede pasar de un ingrediente a otro.
        session.flush()
    for k, values in rows.items():
        obj = existing.get(k)
        if obj is None:
            session.add(model(**dict(zip(key, k, strict=True)), **values))
            changes += 1
        elif changed := {c: v for c, v in values.items() if getattr(obj, c) != v}:
            for c, v in changed.items():
                setattr(obj, c, v)
            changes += 1
    return changes


def _decimal(value) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def apply(session: Session, catalog: Catalog) -> int:
    """Sincroniza la BD con el catálogo; devuelve el número de filas cambiadas."""
    ingredients, substitutes, recipes = catalog
    lost = session.scalars(
        select(Ingredient.slug).join(InventoryItem).where(Ingredient.slug.not_in(ingredients))
    ).all()
    if lost:
        raise CatalogError(
            [
                f"inventario: '{s}' ya no está en ingredients.yaml; restáuralo o quítalo del "
                "inventario"
                for s in lost
            ]
        )

    # Los ingredientes se borran al final: aún pueden tener recetas o hijos que apuntan a ellos.
    changes = _sync(
        session,
        Ingredient,
        ("slug",),
        {
            (slug,): {
                "name": i["name"],
                "kind": i["kind"],
                "is_staple": i.get("is_staple", False),
                "abv": _decimal(i.get("abv")),
            }
            for slug, i in ingredients.items()
        },
        delete=False,
    )
    session.flush()
    ids = dict(session.execute(select(Ingredient.slug, Ingredient.id)).all())
    changes += _sync(
        session,
        Ingredient,
        ("slug",),
        {(slug,): {"parent_id": ids.get(i.get("parent"))} for slug, i in ingredients.items()},
        delete=False,
    )
    changes += _sync(
        session,
        IngredientAlias,
        ("ingredient_id", "alias"),
        {(ids[s], a): {} for s, i in ingredients.items() for a in i.get("aliases") or []},
    )
    changes += _sync(
        session,
        IngredientSubstitute,
        ("ingredient_id", "substitute_id"),
        {
            (ids[s["ingredient"]], ids[s["substitute"]]): {
                "quality": s["quality"],
                "note": s.get("note"),
            }
            for s in substitutes
        },
    )

    # Borrar una receta borra sus filas de recipe_ingredient y recipe_alias (ON DELETE CASCADE).
    fields = ("name", "method", "glass", "instructions", "garnish_text", "source")
    changes += _sync(
        session,
        Recipe,
        ("slug",),
        {
            (slug,): {f: r.get(f) for f in fields} | {"popularity": r.get("popularity", 0)}
            for slug, r in recipes.items()
        },
    )
    session.flush()
    recipe_ids = dict(session.execute(select(Recipe.slug, Recipe.id)).all())
    changes += _sync(
        session,
        RecipeAlias,
        ("recipe_id", "alias"),
        {(recipe_ids[s], a): {} for s, r in recipes.items() for a in r.get("aliases") or []},
    )
    changes += _sync(
        session,
        RecipeIngredient,
        ("recipe_id", "position"),
        {
            (recipe_ids[s], position): {
                "ingredient_id": ids[row["ingredient"]],
                "amount": _decimal(row.get("amount")),
                "unit": row.get("unit"),
                "amount_ml": to_ml(row.get("amount"), row.get("unit")),
                "role": row.get("role", "required"),
                "alt_group": row.get("alt_group"),
            }
            for s, r in recipes.items()
            for position, row in enumerate(r["ingredients"], 1)
        },
    )
    session.flush()
    # Una sola sentencia: la FK de parent_id se comprueba al final, así que borrar padre e
    # hijo juntos no falla. Los hijos que siguen en el YAML tienen padres que también siguen.
    changes += session.execute(
        delete(Ingredient).where(Ingredient.slug.not_in(ingredients))
    ).rowcount
    return changes


def main() -> int:
    try:
        catalog = load_catalog()
        with Session(engine) as session, session.begin():
            changes = apply(session, catalog)
    except CatalogError as e:
        print(f"Seed abortado; la BD no cambió.\n{e}", file=sys.stderr)
        return 1
    print(
        f"Catálogo: {len(catalog.ingredients)} ingredientes, {len(catalog.substitutes)} "
        f"sustitutos, {len(catalog.recipes)} recetas. Filas cambiadas: {changes}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
