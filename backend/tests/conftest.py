"""Fixtures compartidas: BD de pruebas (`docker compose up -d db`) y catálogo en memoria."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, make_url, text

from app.catalog import (
    Ingredient,
    RecipeIngredient,
    RecipeMeta,
    Substitute,
    build_catalog,
)
from app.db import DATABASE_URL

TEST_DB = "mixer_test"
TEST_URL = make_url(DATABASE_URL).set(database=TEST_DB)


@pytest.fixture(scope="module")
def alembic_cfg():
    """Crea una BD de pruebas vacía y la lleva a `head`."""
    admin = create_engine(
        make_url(DATABASE_URL).set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)"))
        conn.execute(text(f"CREATE DATABASE {TEST_DB}"))
    admin.dispose()

    cfg = Config(Path(__file__).parents[1] / "alembic.ini")
    url = TEST_URL.render_as_string(hide_password=False)
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(cfg, "head")
    return cfg


@pytest.fixture(scope="module")
def engine(alembic_cfg):
    engine = create_engine(TEST_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def catalog():
    ingredients = [
        Ingredient(1, "destilado", "Destilados", "category"),
        Ingredient(2, "ron", "Ron", "generic", parent_id=1),
        Ingredient(3, "ron-blanco", "Ron blanco", "generic", parent_id=2),
        Ingredient(4, "bacardi-carta-blanca", "Bacardí Carta Blanca", "brand", parent_id=3),
        Ingredient(5, "ron-anejo", "Ron añejo", "generic", parent_id=2),
        Ingredient(24, "havana-7", "Havana Club 7", "brand", parent_id=5),
        Ingredient(27, "ron-oscuro", "Ron oscuro", "generic", parent_id=2),
        Ingredient(6, "jugo-de-lima", "Jugo de lima", "generic"),
        Ingredient(7, "azucar", "Azúcar", "generic", is_staple=True),
        Ingredient(8, "hielo", "Hielo", "generic", is_staple=True),
        Ingredient(23, "whiskey-americano", "Whiskey americano", "generic", parent_id=1),
        Ingredient(9, "bourbon", "Bourbon", "generic", parent_id=23),
        Ingredient(10, "rye", "Whiskey de centeno", "generic", parent_id=23),
        Ingredient(28, "makers-mark", "Maker's Mark", "brand", parent_id=9),
        Ingredient(11, "menta", "Menta", "generic"),
        Ingredient(12, "soda", "Soda", "generic"),
        Ingredient(13, "jarabe-simple", "Jarabe simple", "generic"),
        Ingredient(14, "ginebra", "Ginebra", "generic", parent_id=1),
        Ingredient(15, "london-dry", "London Dry", "generic", parent_id=14),
        Ingredient(16, "tanqueray", "Tanqueray", "brand", parent_id=15),
        Ingredient(20, "crema-de-cacao", "Crema de cacao", "generic"),
        Ingredient(21, "crema-de-cacao-blanca", "Crema de cacao blanca", "generic"),
        Ingredient(22, "licor-de-cafe", "Licor de café", "generic"),
    ]
    substitutes = [
        Substitute(ingredient_id=3, substitute_id=5, quality=2),
        Substitute(ingredient_id=3, substitute_id=27, quality=1),
        Substitute(ingredient_id=13, substitute_id=7, quality=3),
        # Cadena A→B, B→C: no debe aplicarse transitivamente.
        Substitute(ingredient_id=20, substitute_id=21, quality=3),
        Substitute(ingredient_id=21, substitute_id=22, quality=3),
    ]
    recipes = [
        RecipeMeta(1, "daiquiri", "Daiquirí", popularity=85),
        RecipeMeta(2, "whiskey", "Whiskey", popularity=50),
        RecipeMeta(3, "gin-tonic", "Gin Tonic"),
        RecipeMeta(4, "chain", "Cadena"),
        RecipeMeta(5, "syrup", "Jarabe"),
        RecipeMeta(6, "basics", "Solo básicos"),
        RecipeMeta(7, "ron-generic", "Ron genérico"),
        # Para el ranking: mismo m, distinta cobertura relativa y popularidad.
        RecipeMeta(8, "two", "Dos", popularity=99),
        RecipeMeta(9, "four", "Cuatro"),
        RecipeMeta(10, "subbed", "Con sustituto"),
        RecipeMeta(11, "mojito", "Mojito", popularity=90),
    ]
    recipe_ingredients = [
        RecipeIngredient(1, 3, 1),
        RecipeIngredient(1, 6, 2),
        RecipeIngredient(1, 7, 3),
        # "Bourbon o rye" + filas informativas que no cuentan como requisitos.
        RecipeIngredient(2, 9, 1, alt_group=1),
        RecipeIngredient(2, 10, 2, alt_group=1),
        RecipeIngredient(2, 6, 3, role="optional"),
        RecipeIngredient(2, 7, 4, role="garnish"),
        RecipeIngredient(3, 15, 1),
        RecipeIngredient(3, 12, 2),
        RecipeIngredient(3, 8, 3),
        RecipeIngredient(4, 20, 1),
        RecipeIngredient(5, 13, 1),
        RecipeIngredient(6, 7, 1),
        RecipeIngredient(6, 8, 2),
        RecipeIngredient(7, 2, 1),
        RecipeIngredient(8, 3, 1),
        RecipeIngredient(8, 11, 2),
        RecipeIngredient(9, 3, 1),
        RecipeIngredient(9, 6, 2),
        RecipeIngredient(9, 8, 3),
        RecipeIngredient(9, 11, 4),
        RecipeIngredient(10, 13, 1),
        RecipeIngredient(10, 11, 2),
        RecipeIngredient(11, 3, 1),
        RecipeIngredient(11, 6, 2),
        RecipeIngredient(11, 7, 3),
        RecipeIngredient(11, 11, 4),
        RecipeIngredient(11, 12, 5),
    ]
    return build_catalog(ingredients, substitutes, recipes, recipe_ingredients)
