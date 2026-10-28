"""Pruebas del seed (F2.T5): idempotencia y aborto sin escribir.

Requieren `docker compose up -d db`. Cada prueba ejecuta `scripts.seed.main()` contra
`mixer_test` con una copia desechable de `data/`, así que el catálogo real no se toca.
"""

import shutil
from pathlib import Path

import pytest
import yaml
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models import (
    Ingredient,
    IngredientAlias,
    IngredientSubstitute,
    InventoryItem,
    Recipe,
    RecipeAlias,
    RecipeImage,
    RecipeIngredient,
)
from scripts import seed

DATA_DIR = Path(__file__).parents[1] / "data"
MODELS = (
    Ingredient,
    IngredientAlias,
    IngredientSubstitute,
    Recipe,
    RecipeAlias,
    RecipeImage,
    RecipeIngredient,
    InventoryItem,
)


@pytest.fixture(autouse=True)
def empty_db(engine):
    """Cada prueba parte de una BD vacía (el motor es de alcance de módulo)."""
    tables = ", ".join(m.__tablename__ for m in MODELS)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture
def data_dir(tmp_path):
    """Copia desechable de data/ para modificarla sin tocar el catálogo real."""
    dest = tmp_path / "data"
    shutil.copytree(DATA_DIR, dest)
    return dest


def seed_rows(engine) -> dict[str, int]:
    with Session(engine) as s:
        return {m.__tablename__: s.scalar(select(func.count()).select_from(m)) for m in MODELS}


def edit_yaml(path: Path, mutate) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def run_seed(engine, data_dir: Path, monkeypatch) -> int:
    """`python -m scripts.seed` contra la BD de pruebas con la copia indicada."""
    monkeypatch.setattr(seed, "DATA_DIR", data_dir)
    monkeypatch.setattr(seed, "engine", engine)
    monkeypatch.setattr(seed, "notify_api", lambda: print("API notificada"))
    return seed.main()


def test_second_run_changes_nothing(engine, data_dir, monkeypatch, capsys):
    assert run_seed(engine, data_dir, monkeypatch) == 0
    out = capsys.readouterr().out
    assert "Filas cambiadas: 0." not in out and "API notificada" in out
    rows = seed_rows(engine)
    assert rows["recipe"] > 0 and rows["ingredient"] > 0 and rows["recipe_image"] > 0

    assert run_seed(engine, data_dir, monkeypatch) == 0
    out = capsys.readouterr().out
    assert "Filas cambiadas: 0." in out and "API notificada" not in out
    assert seed_rows(engine) == rows


def test_cycle_aborts_without_writing(engine, data_dir, monkeypatch, capsys):
    assert run_seed(engine, data_dir, monkeypatch) == 0
    capsys.readouterr()
    rows = seed_rows(engine)

    def make_cycle(taxonomy):
        by_slug = {item["slug"]: item for item in taxonomy["ingredients"]}
        by_slug["destilado"]["parent"] = "ron-blanco"

    edit_yaml(data_dir / "ingredients.yaml", make_cycle)
    assert run_seed(engine, data_dir, monkeypatch) == 1
    err = capsys.readouterr().err
    assert "ciclo en la jerarquía" in err
    assert "la BD no cambió" in err
    assert seed_rows(engine) == rows


def test_broken_reference_aborts_without_writing(engine, data_dir, monkeypatch, capsys):
    assert run_seed(engine, data_dir, monkeypatch) == 0
    capsys.readouterr()
    rows = seed_rows(engine)

    def break_reference(recipe):
        recipe["ingredients"][0]["ingredient"] = "ron-inexistente"

    edit_yaml(data_dir / "recipes" / "daiquiri.yaml", break_reference)
    assert run_seed(engine, data_dir, monkeypatch) == 1
    err = capsys.readouterr().err
    assert "daiquiri.yaml: ron-inexistente" in err
    assert "no existe" in err
    assert seed_rows(engine) == rows


def test_invalid_yaml_aborts_without_writing(engine, data_dir, monkeypatch, capsys):
    assert run_seed(engine, data_dir, monkeypatch) == 0
    capsys.readouterr()
    rows = seed_rows(engine)

    (data_dir / "ingredients.yaml").write_text("ingredients: [", encoding="utf-8")
    assert run_seed(engine, data_dir, monkeypatch) == 1
    err = capsys.readouterr().err
    assert "ingredients.yaml: no se puede leer" in err
    assert "la BD no cambió" in err
    assert seed_rows(engine) == rows


def test_inventory_ingredient_removal_aborts(engine, data_dir, monkeypatch, capsys):
    assert run_seed(engine, data_dir, monkeypatch) == 0
    capsys.readouterr()
    with Session(engine) as s, s.begin():
        brand = s.scalar(select(Ingredient).where(Ingredient.slug == "bacardi-carta-blanca"))
        s.add(InventoryItem(ingredient_id=brand.id))
    rows = seed_rows(engine)

    def drop_brand(taxonomy):
        taxonomy["ingredients"] = [
            item for item in taxonomy["ingredients"] if item["slug"] != "bacardi-carta-blanca"
        ]

    edit_yaml(data_dir / "ingredients.yaml", drop_brand)
    assert run_seed(engine, data_dir, monkeypatch) == 1
    err = capsys.readouterr().err
    assert "inventario: 'bacardi-carta-blanca'" in err
    assert "la BD no cambió" in err
    assert seed_rows(engine) == rows


def test_recipe_named_like_another_aborts(data_dir):
    # "The Last Word" repite "Last Word": la clave ignora mayúsculas, puntuación y relleno.
    shutil.copy(
        data_dir / "recipes" / "last-word.yaml", data_dir / "recipes" / "the-last-word.yaml"
    )
    edit_yaml(
        data_dir / "recipes" / "the-last-word.yaml",
        lambda r: r.update(slug="the-last-word", name="The Last-Word Cocktail"),
    )
    with pytest.raises(seed.CatalogError, match="Cocktail' repite .* recipes/last-word.yaml"):
        seed.load_catalog(data_dir)


def test_broken_image_manifest_aborts(data_dir):
    (data_dir / "images.yaml").write_text(
        "daiquiri: {file: no-existe.webp}\n"
        "negroni: {file: ../ingredients.yaml}\n"
        "receta-fantasma: {file: daiquiri.webp}\n",
        encoding="utf-8",
    )
    with pytest.raises(seed.CatalogError) as e:
        seed.load_catalog(data_dir)
    assert "images.yaml: daiquiri: no existe images/no-existe.webp" in str(e.value)
    assert "images.yaml: negroni: '../ingredients.yaml' debe ser un nombre de archivo" in str(
        e.value
    )
    assert "images.yaml: receta-fantasma: la receta no existe" in str(e.value)


def test_recipes_without_image_are_valid(data_dir):
    (data_dir / "images.yaml").unlink()
    assert seed.load_catalog(data_dir).images == {}


def test_unknown_or_repeated_flavor_aborts(data_dir):
    edit_yaml(data_dir / "recipes" / "daiquiri.yaml", lambda r: r.update(flavors=["sour", "acido"]))
    edit_yaml(
        data_dir / "recipes" / "negroni.yaml", lambda r: r.update(flavors=["bitter", "bitter"])
    )
    with pytest.raises(seed.CatalogError) as e:
        seed.load_catalog(data_dir)
    assert "recipes/daiquiri.yaml: flavors ['acido'] no son de" in str(e.value)
    assert "recipes/negroni.yaml: flavors debe ser una lista sin repetidos" in str(e.value)
