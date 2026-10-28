"""Pruebas de `scripts.fetch_iba_images` sin red: `_get` se sustituye por respuestas fijas."""

import urllib.error

from scripts import fetch_iba_images
from scripts.fetch_iba_images import PAGE, featured_image

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

    monkeypatch.setattr(fetch_iba_images, "_get", fake_get)
    known = {"negroni": {"file": "negroni.webp", "source": PAGE.format(slug="negroni")}}

    manifest = fetch_iba_images.fetch(["caida", "daiquiri", "negroni", "sin-foto"], tmp_path, known)

    # La web caída o una ficha sin imagen dejan la receta sin foto, sin abortar.
    assert manifest == known | {
        "daiquiri": {"file": "daiquiri.webp", "source": PAGE.format(slug="daiquiri")}
    }
    assert (tmp_path / "daiquiri.webp").read_bytes() == b"RIFF-webp"
    # Las ya anotadas no se vuelven a pedir.
    assert PAGE.format(slug="negroni") not in requested
