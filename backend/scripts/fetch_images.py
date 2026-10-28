"""Fotos de las recetas: `python -m scripts.fetch_images`.

Las recetas con `source: iba` toman la imagen destacada de su ficha en iba-world.com
(`/iba-cocktail/<slug>/`, mismos slugs que el catálogo); las de `source: thecocktaildb`, la
miniatura de TheCocktailDB, buscada por el id que su YAML anota en la primera línea. Cada foto
se descarga a data/images/<slug>.<ext> y se anota en data/images.yaml, que el seed carga en
recipe_image. Las ya anotadas no se vuelven a pedir. Si la web no responde o no hay imagen, lo
avisa y sigue: la receta queda sin foto y la API nunca depende de la web externa. Tras
ejecutarlo, `python -m scripts.seed`.
"""

import json
import re
import sys
import urllib.request
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

import yaml

from scripts.seed import DATA_DIR, load_catalog

PAGE = "https://iba-world.com/iba-cocktail/{slug}/"
# WordPress publica la imagen destacada en la configuración de Elementor, con "\/" escapadas.
FEATURED = re.compile(r'"featuredImage":"([^"]+)"')
LOOKUP = "https://www.thecocktaildb.com/api/json/v1/1/lookup.php?i={id}"
DRINK = "https://www.thecocktaildb.com/drink/{id}"
# Primera línea de los YAML que escribe scripts.import_cocktaildb.
COCKTAILDB_ID = re.compile(r"# TheCocktailDB #(\d+)")
HEADER = "# Fotos de las recetas (data/images/). Lo genera scripts.fetch_images.\n"

# slug → (página de origen, URL de la imagen o None si no la hay).
Locate = Callable[[str], tuple[str, str | None]]


def _get(url: str) -> bytes:
    # Sin User-Agent de navegador la web responde 403.
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def featured_image(html: str) -> str | None:
    """URL de la imagen destacada de una ficha, o None si no la trae."""
    match = FEATURED.search(html)
    return json.loads(f'"{match[1]}"') if match else None


def locate_iba(slug: str) -> tuple[str, str | None]:
    page = PAGE.format(slug=slug)
    return page, featured_image(_get(page).decode("utf-8", "replace"))


def locate_cocktaildb(drink_id: str) -> tuple[str, str | None]:
    drinks = json.loads(_get(LOOKUP.format(id=drink_id)))["drinks"] or []
    thumb = drinks[0]["strDrinkThumb"] if drinks else None
    # El tamaño medio (350 px) basta para tarjetas y detalle; el original pesa ~5 veces más.
    return DRINK.format(id=drink_id), thumb and thumb + "/medium"


def fetch(
    slugs, images_dir: Path, manifest: dict[str, dict], locate: Locate = locate_iba
) -> dict[str, dict]:
    """Descarga las fotos que faltan en `manifest` y lo devuelve ampliado; los fallos se omiten."""
    manifest = dict(manifest)
    images_dir.mkdir(parents=True, exist_ok=True)
    for slug in slugs:
        if slug in manifest:
            continue
        try:
            page, url = locate(slug)
            if url is None:
                raise ValueError("la ficha no trae imagen")
            # TheCocktailDB sirve los tamaños como /<foto>.jpg/medium.
            path = PurePosixPath(urlparse(url).path)
            file = slug + (path.suffix or path.parent.suffix)
            (images_dir / file).write_bytes(_get(url))
        except (OSError, ValueError, KeyError) as e:
            print(f"{slug}: sin foto ({e})", file=sys.stderr)
            continue
        manifest[slug] = {"file": file, "source": page}
    return manifest


def main() -> int:
    catalog = load_catalog()
    path = DATA_DIR / "images.yaml"
    old = (yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else None) or {}
    by_source: dict[str, list[str]] = {}
    for slug, recipe in sorted(catalog.recipes.items()):
        by_source.setdefault(recipe.get("source"), []).append(slug)
    manifest = fetch(by_source.get("iba", []), DATA_DIR / "images", old)
    ids = {}
    for slug in by_source.get("thecocktaildb", []):
        text = (DATA_DIR / "recipes" / f"{slug}.yaml").read_text(encoding="utf-8")
        if match := COCKTAILDB_ID.match(text):
            ids[slug] = match[1]
    manifest = fetch(
        sorted(ids), DATA_DIR / "images", manifest, lambda slug: locate_cocktaildb(ids[slug])
    )
    body = yaml.safe_dump(dict(sorted(manifest.items())), allow_unicode=True, sort_keys=False)
    path.write_text(HEADER + body, encoding="utf-8")
    total = sum(map(len, by_source.values()))
    print(f"Fotos: {len(manifest)} de {total} recetas ({len(manifest) - len(old)} nuevas).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
