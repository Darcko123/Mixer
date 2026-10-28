"""Fotos de las recetas IBA desde iba-world.com: `python -m scripts.fetch_iba_images`.

Para cada receta con `source: iba` lee su ficha (`/iba-cocktail/<slug>/`, mismos slugs que el
catálogo), descarga la imagen destacada a data/images/<slug>.<ext> y la anota en
data/images.yaml, que el seed carga en recipe_image. Las ya anotadas no se vuelven a pedir.
Si la web no responde o una ficha no trae imagen, lo avisa y sigue: la receta queda sin foto
y la API nunca depende de la web externa. Tras ejecutarlo, `python -m scripts.seed`.
"""

import json
import re
import sys
import urllib.request
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

import yaml

from scripts.seed import DATA_DIR, load_catalog

PAGE = "https://iba-world.com/iba-cocktail/{slug}/"
# WordPress publica la imagen destacada en la configuración de Elementor, con "\/" escapadas.
FEATURED = re.compile(r'"featuredImage":"([^"]+)"')
HEADER = "# Fotos de las recetas (data/images/). Lo genera scripts.fetch_iba_images.\n"


def _get(url: str) -> bytes:
    # Sin User-Agent de navegador la web responde 403.
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def featured_image(html: str) -> str | None:
    """URL de la imagen destacada de una ficha, o None si no la trae."""
    match = FEATURED.search(html)
    return json.loads(f'"{match[1]}"') if match else None


def fetch(slugs, images_dir: Path, manifest: dict[str, dict]) -> dict[str, dict]:
    """Descarga las fotos que faltan en `manifest` y lo devuelve ampliado; los fallos se omiten."""
    manifest = dict(manifest)
    images_dir.mkdir(parents=True, exist_ok=True)
    for slug in slugs:
        if slug in manifest:
            continue
        page = PAGE.format(slug=slug)
        try:
            url = featured_image(_get(page).decode("utf-8", "replace"))
            if url is None:
                raise ValueError("la ficha no trae imagen destacada")
            file = slug + PurePosixPath(urlparse(url).path).suffix
            (images_dir / file).write_bytes(_get(url))
        except (OSError, ValueError) as e:
            print(f"{slug}: sin foto ({e})", file=sys.stderr)
            continue
        manifest[slug] = {"file": file, "source": page}
    return manifest


def main() -> int:
    catalog = load_catalog()
    path = DATA_DIR / "images.yaml"
    old = (yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else None) or {}
    slugs = sorted(s for s, r in catalog.recipes.items() if r.get("source") == "iba")
    manifest = fetch(slugs, DATA_DIR / "images", old)
    body = yaml.safe_dump(dict(sorted(manifest.items())), allow_unicode=True, sort_keys=False)
    path.write_text(HEADER + body, encoding="utf-8")
    new = len(manifest) - len(old)
    print(f"Fotos: {len(manifest)} de {len(slugs)} recetas IBA ({new} nuevas).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
