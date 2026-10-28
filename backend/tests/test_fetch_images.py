"""Pruebas de `scripts.fetch_images` sin red: `_get` se sustituye por respuestas fijas."""

import urllib.error

from scripts import fetch_images
from scripts.fetch_images import DRINK, LOOKUP, PAGE, featured_image, locate_cocktaildb

# Fragmento real de https://iba-world.com/iba-cocktail/daiquiri/ (configuración de Elementor).
HTML = (
    '"post":{"id":205,"title":"Daiquiri%20%E2%80%93%20IBA","excerpt":"","featuredImage":'
    '"https:\\/\\/iba-world.com\\/wp-content\\/uploads\\/2024\\/07\\/'
    'iba-cocktail-the-unforgettables-daiquiri-6694910c5866e-682x1024.webp"}};'
)
IMAGE = "https://iba-world.com/wp-content/uploads/2024/07/iba-cocktail-the-unforgettables-daiquiri-6694910c5866e-682x1024.webp"


def test_featured_image():
    assert featured_image(HTML) == IMAGE
    assert featured_image("<html>sin imagen</html>") is None


def test_fetch_skips_failures_and_known_images(tmp_path, monkeypatch):
    responses = {
        PAGE.format(slug="daiquiri"): HTML.encode(),
        IMAGE: b"RIFF-webp",
        PAGE.format(slug="sin-foto"): b"<html></html>",
    }
    requested = []

    def fake_get(url):
        requested.append(url)
        if url not in responses:
            raise urllib.error.URLError("timed out")
        return responses[url]

    monkeypatch.setattr(fetch_images, "_get", fake_get)
    known = {"negroni": {"file": "negroni.webp", "source": PAGE.format(slug="negroni")}}

    manifest = fetch_images.fetch(["caida", "daiquiri", "negroni", "sin-foto"], tmp_path, known)

    # La web caída o una ficha sin imagen dejan la receta sin foto, sin abortar.
    assert manifest == known | {
        "daiquiri": {"file": "daiquiri.webp", "source": PAGE.format(slug="daiquiri")}
    }
    assert (tmp_path / "daiquiri.webp").read_bytes() == b"RIFF-webp"
    # Las ya anotadas no se vuelven a pedir.
    assert PAGE.format(slug="negroni") not in requested


def test_fetch_cocktaildb_thumbnail(tmp_path, monkeypatch):
    thumb = "https://www.thecocktaildb.com/images/media/drink/2x8thr1504816928.jpg"
    original = "https://www.thecocktaildb.com/images/media/drink/o9m9wy1790013164.jpg"
    responses = {
        LOOKUP.format(id="17222"): b'{"drinks": [{"strDrinkThumb": "%s"}]}' % thumb.encode(),
        LOOKUP.format(id="178372"): b'{"drinks": [{"strDrinkThumb": "%s"}]}' % original.encode(),
        LOOKUP.format(id="1"): b'{"drinks": null}',
        thumb + "/medium": b"JFIF",
        original: b"JFIF-original",
    }

    def fake_get(url):
        if url not in responses:
            raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
        return responses[url]

    monkeypatch.setattr(fetch_images, "_get", fake_get)
    ids = {"a1": "17222", "boyarsky": "178372", "borrada": "1"}

    manifest = fetch_images.fetch(ids, tmp_path, {}, lambda slug: locate_cocktaildb(ids[slug]))

    # La extensión sale de la foto aunque la URL del tamaño medio acabe en /medium.
    assert manifest == {
        "a1": {"file": "a1.jpg", "source": DRINK.format(id="17222")},
        "boyarsky": {"file": "boyarsky.jpg", "source": DRINK.format(id="178372")},
    }
    assert (tmp_path / "a1.jpg").read_bytes() == b"JFIF"
    # Sin tamaño medio, el original.
    assert (tmp_path / "boyarsky.jpg").read_bytes() == b"JFIF-original"
