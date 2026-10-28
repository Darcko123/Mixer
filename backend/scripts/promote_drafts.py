"""Promueve los borradores de data/recipes/_import/ al catálogo: `python -m scripts.promote_drafts`.

Copia a data/recipes/ cada borrador con todos los ingredientes resueltos, salvo:
- los que repiten el slug, el nombre o un alias (por `seed.name_key`) de una receta del
  catálogo o de un borrador anterior en orden alfabético;
- los descartados en la revisión (SKIP) y los licores caseros, que no son cócteles;
- los que la validación del seed rechaza (se imprime el motivo).
Lo ya promovido cuenta como duplicado, así que repetirlo no cambia nada. Revisar el
resultado con `git diff` antes de versionarlo.
"""

import shutil
import sys
import tempfile
from pathlib import Path

import yaml

from scripts.import_cocktaildb import OUT_DIR
from scripts.seed import DATA_DIR, CatalogError, load_catalog, name_key

RECIPES_DIR = DATA_DIR / "recipes"
# Duplicados que la clave de nombre no detecta, decididos al revisar los borradores.
SKIP = {
    "cuba-libra": "variante de cuba-libre con el nombre mal escrito",
    "martinez-2": "variante de martinez",
    "vodka-and-tonic": "duplicado de vodka-tonic, que trae las cantidades",
}


def candidates() -> tuple[dict[str, str], list[str]]:
    """Borradores promovibles {slug: YAML} y los descartados con su motivo."""
    taken = {}
    for slug, recipe in load_catalog().recipes.items():
        for name in [slug, recipe["name"], *(recipe.get("aliases") or [])]:
            taken[name_key(name)] = slug
    promoted, skipped = {}, []
    for path in sorted(OUT_DIR.glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        if "SIN RESOLVER" in text:
            continue
        draft = yaml.safe_load(text)
        slug = draft["slug"]
        keys = [name_key(n) for n in [slug, draft["name"], *(draft.get("aliases") or [])]]
        duplicate = next((taken[k] for k in keys if k in taken), None)
        reason = (
            SKIP.get(slug)
            or ("licor casero" if "Homemade Liqueur" in text.partition("\n")[0] else None)
            or (duplicate and f"duplicado de {duplicate}")
        )
        if reason:
            skipped.append(f"{slug}: {reason}")
            continue
        taken.update(dict.fromkeys(keys, slug))
        promoted[slug] = text.replace("# Borrador de TheCocktailDB", "# TheCocktailDB", 1).replace(
            " Revisar antes de mover a data/recipes/.", "", 1
        )
    return promoted, skipped


def reject_invalid(promoted: dict[str, str]) -> list[str]:
    """Quita de `promoted` los borradores que el seed rechaza; devuelve sus errores."""
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp)
        shutil.copytree(
            DATA_DIR, data, ignore=shutil.ignore_patterns("_import"), dirs_exist_ok=True
        )
        for slug, text in promoted.items():
            (data / "recipes" / f"{slug}.yaml").write_text(text, encoding="utf-8")
        try:
            load_catalog(data)
        except CatalogError as e:
            errors = str(e).splitlines()
        else:
            return []
    bad = {line.removeprefix("recipes/").partition(".yaml:")[0] for line in errors}
    if not bad & promoted.keys():
        # El catálogo ya era inválido sin los borradores.
        raise CatalogError(errors)
    for slug in bad & promoted.keys():
        del promoted[slug]
    return [line.removeprefix("recipes/").replace(".yaml:", ":", 1) for line in errors]


def main() -> int:
    try:
        promoted, skipped = candidates()
        # Un rechazo no afecta a los demás borradores, pero se comprueba hasta que no quede ninguno.
        while rejected := reject_invalid(promoted):
            skipped += rejected
    except CatalogError as e:
        print(f"El catálogo actual no es válido; no se promueve nada.\n{e}", file=sys.stderr)
        return 1
    for slug, text in promoted.items():
        (RECIPES_DIR / f"{slug}.yaml").write_text(text, encoding="utf-8")
    print("\n".join(f"Descartado {line}" for line in skipped))
    print(f"{len(promoted)} borradores promovidos a data/recipes/; {len(skipped)} descartados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
