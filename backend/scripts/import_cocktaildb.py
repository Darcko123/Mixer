"""Borradores de recetas desde TheCocktailDB: `python -m scripts.import_cocktaildb`.

Descarga todas las bebidas (búsqueda por inicial, clave pública de pruebas: solo uso
personal), resuelve cada ingrediente contra los slugs y alias de ingredients.yaml y escribe
un YAML por receta en data/recipes/_import/, que el seed no lee. Los ingredientes sin
resolver quedan como "SIN RESOLVER: <nombre>" para que el seed los rechace si se promueve
el borrador sin revisarlo. Cada fila conserva la medida original en un comentario.
_import/unmapped.txt lista esos nombres por frecuencia: ampliar la taxonomía con los más
comunes y volver a ejecutar.
"""

import json
import re
import string
import sys
import urllib.request
from collections import Counter
from fractions import Fraction

from scripts.seed import DATA_DIR, load_catalog, normalize

API = "https://www.thecocktaildb.com/api/json/v1/1/search.php?f="
OUT_DIR = DATA_DIR / "recipes" / "_import"

# Unidad de TheCocktailDB → (unidad del catálogo, factor). Las de volumen sin equivalente
# pasan a oz o ml; "part" no tiene volumen fijo y queda sin cantidad.
UNITS = {
    "oz": ("oz", 1),
    "shot": ("oz", Fraction(3, 2)),
    "jigger": ("oz", Fraction(3, 2)),
    "measure": ("oz", Fraction(3, 2)),
    "cup": ("oz", 8),
    "pint": ("oz", 16),
    "qt": ("oz", 32),
    "gal": ("oz", 128),
    "cl": ("cl", 1),
    "dl": ("cl", 10),
    "ml": ("ml", 1),
    "l": ("ml", 1000),
    "fifth": ("ml", 750),
    "tsp": ("tsp", 1),
    "tbsp": ("tbsp", 1),
    "tblsp": ("tbsp", 1),
    "dash": ("dash", 1),
    "drop": ("gota", 1),
    "slice": ("rodaja", 1),
    "sprig": ("ramita", 1),
    "leaf": ("hoja", 1),
    "leaves": ("hoja", 1),
    "piece": ("pieza", 1),
    "wedge": ("pieza", 1),
    "whole": ("pieza", 1),
    "chunk": ("pieza", 1),
    "cube": ("pieza", 1),
}
NUMBER = r"\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?|½"
MEASURE = re.compile(rf"({NUMBER})(?:\s*(?:-|or)\s*(?:{NUMBER}))?\s*([a-z]*)")

GLASSES = {
    "cocktail": "cocktail",
    "martini": "cocktail",
    "nick and nora": "cocktail",
    "margarita/coupette": "coupe",
    "margarita": "coupe",
    "coupe": "coupe",
    "champagne flute": "flute",
    "old-fashioned": "old-fashioned",
    "whiskey": "old-fashioned",
    "white wine": "wine",
    "balloon": "wine",
    "irish coffee cup": "irish-coffee",
    "copper mug": "mule-cup",
}
# Palabra clave de las instrucciones en inglés → method; gana la primera que aparece aquí.
METHODS = ["blend", "muddle", "shake", "stir"]


def parse_measure(text: str | None) -> tuple[int | float | None, str | None]:
    """Medida en texto libre → (amount, unit) del catálogo, o (None, None) si no hay cantidad.

    "1 1/2 oz" → (1.5, "oz"); "Juice of 1/2" → (0.5, "pieza"); "2-3 oz" → (2, "oz");
    "1 shot" → (1.5, "oz"); "Dash" → (1, "dash"); "Top", "1 part", "1 can" → (None, None).
    """
    text = (text or "").strip().lower().removeprefix("juice of").strip()
    match = MEASURE.match(text)
    if not match:
        return (1, "dash") if text.startswith("dash") else (None, None)
    number, word = match.groups()
    plurals = (word, word.removesuffix("s"), word.removesuffix("es"))
    found = ("pieza", 1) if not word else next(filter(None, map(UNITS.get, plurals)), None)
    if found is None:
        return None, None
    unit, factor = found
    amount = sum(Fraction(n) for n in number.replace("½", "1/2").split()) * factor
    if unit == "ml":
        return round(amount), unit
    return (int(amount) if amount.denominator == 1 else round(float(amount), 2)), unit


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normalize(text)).strip("-")


def download() -> list[dict]:
    drinks = {}
    for initial in string.ascii_lowercase + string.digits:
        with urllib.request.urlopen(API + initial, timeout=30) as response:
            for drink in json.load(response)["drinks"] or []:
                drinks[drink["idDrink"]] = drink
    return sorted(drinks.values(), key=lambda d: d["strDrink"])


def name_index(ingredients: dict[str, dict]) -> dict[str, str]:
    """Nombre o alias normalizado → slug del genérico que citaría una receta."""
    index = {}
    for slug, item in ingredients.items():
        if item["kind"] == "category":
            continue
        cited = item["parent"] if item["kind"] == "brand" else slug
        for name in [item["name"], *(item.get("aliases") or [])]:
            index[normalize(name)] = cited
    return index


def draft(
    drink: dict, slug: str, ingredients: dict[str, dict], index: dict[str, str]
) -> tuple[str, list[str]]:
    """YAML del borrador y nombres de los ingredientes sin resolver."""
    unresolved = []
    rows = []
    for i in range(1, 16):
        name = (drink[f"strIngredient{i}"] or "").strip()
        if not name:
            continue
        raw = (drink[f"strMeasure{i}"] or "").strip()
        cited = index.get(normalize(name))
        if cited is None:
            unresolved.append(name)
            cited = json.dumps(f"SIN RESOLVER: {name}", ensure_ascii=False)
        elif raw.lower().startswith("juice of"):
            # La fruta cuelga de su jugo: "Juice of 1/2" + Lemon pide el jugo, no la fruta.
            parent = ingredients[cited].get("parent") or ""
            cited = parent if parent.startswith("jugo-") else cited
        amount, unit = parse_measure(raw)
        row = f"ingredient: {cited}"
        if amount is not None:
            row += f", amount: {amount}, unit: {unit}"
        if raw.lower().startswith("garnish"):
            row += ", role: garnish"
        rows.append(f"  - {{{row}}}  # {name}" + (f" — {raw}" if raw else ""))

    instructions = drink.get("strInstructionsES") or drink["strInstructions"] or ""
    english = (drink["strInstructions"] or "").lower()
    glass = (drink["strGlass"] or "").lower().removesuffix(" glass")
    lines = [
        f"# Borrador de TheCocktailDB #{drink['idDrink']} ({drink['strAlcoholic']}, "
        f"{drink['strCategory']}). Revisar antes de mover a data/recipes/.",
        f"slug: {slug}",
        f"name: {json.dumps(drink['strDrink'], ensure_ascii=False)}",
    ]
    if alternate := drink.get("strDrinkAlternate"):
        lines.append(f"aliases: [{json.dumps(alternate, ensure_ascii=False)}]")
    method = next((m for m in METHODS if m in english), "build")
    lines += [f"method: {method}", f"glass: {GLASSES.get(glass, slugify(glass))}"]
    lines += ["source: thecocktaildb", "ingredients:", *rows]
    lines.append(f"instructions: {json.dumps(instructions.strip(), ensure_ascii=False)}")
    return "\n".join(lines) + "\n", unresolved


def main() -> int:
    ingredients = load_catalog().ingredients
    index = name_index(ingredients)
    drinks = download()
    OUT_DIR.mkdir(exist_ok=True)
    complete = 0
    unmapped = Counter()
    written = set()
    for drink in drinks:
        slug = slugify(drink["strDrink"])
        # La fuente repite alguna bebida ("Planter's Punch" con ' y ’): se conservan ambas.
        slug = f"{slug}-{drink['idDrink']}" if slug in written else slug
        written.add(slug)
        text, unresolved = draft(drink, slug, ingredients, index)
        (OUT_DIR / f"{slug}.yaml").write_text(text, encoding="utf-8")
        complete += not unresolved
        unmapped.update(map(normalize, unresolved))
    report = "".join(f"{count:4}  {name}\n" for name, count in unmapped.most_common())
    (OUT_DIR / "unmapped.txt").write_text(report, encoding="utf-8")
    print(
        f"{len(drinks)} borradores en {OUT_DIR.relative_to(DATA_DIR.parent)}; "
        f"{complete} con todos los ingredientes resueltos; "
        f"{len(unmapped)} nombres sin resolver en unmapped.txt."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
