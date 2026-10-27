"""Pruebas de las estructuras en memoria del catálogo (F3.T1)."""

import shutil
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.catalog import (
    Ingredient,
    RecipeIngredient,
    RecipeMeta,
    Substitute,
    build_catalog,
    load_catalog,
)
from scripts import seed

DATA_DIR = Path(__file__).parents[1] / "data"


def test_build_catalog_structures():
    ingredients = [
        Ingredient(1, "destilado", "Destilados", "category"),
        Ingredient(2, "ron", "Ron", "generic", parent_id=1),
        Ingredient(3, "ron-blanco", "Ron blanco", "generic", parent_id=2),
        Ingredient(4, "bacardi-carta-blanca", "Bacardí Carta Blanca", "brand", parent_id=3),
        Ingredient(5, "ron-anejo", "Ron añejo", "generic", parent_id=2),
        Ingredient(6, "jugo-de-lima", "Jugo de lima", "generic"),
        Ingredient(7, "azucar", "Azúcar", "generic", is_staple=True),
        Ingredient(8, "bourbon", "Bourbon", "generic"),
        Ingredient(9, "rye", "Whiskey de centeno", "generic"),
    ]
    substitutes = [Substitute(ingredient_id=3, substitute_id=5, quality=2)]
    recipes = [
        RecipeMeta(1, "daiquiri", "Daiquirí", popularity=85),
        RecipeMeta(2, "whiskey", "Whiskey", popularity=50),
    ]
    recipe_ingredients = [
        RecipeIngredient(1, 3, 1, amount=Decimal("60"), unit="ml", amount_ml=60),
        RecipeIngredient(1, 6, 2),
        RecipeIngredient(1, 7, 3),
        # "Bourbon o rye" + filas informativas que no cuentan como requisitos.
        RecipeIngredient(2, 8, 1, alt_group=1),
        RecipeIngredient(2, 9, 2, alt_group=1),
        RecipeIngredient(2, 6, 3, role="optional"),
        RecipeIngredient(2, 7, 4, role="garnish"),
    ]

    catalog = build_catalog(ingredients, substitutes, recipes, recipe_ingredients)

    assert catalog.ingredients_by_slug["ron-blanco"].id == 3
    # Tener la marca cubre el genérico y toda la cadena de ancestros.
    assert catalog.ancestors_or_self[4] == frozenset({1, 2, 3, 4})
    assert catalog.ancestors_or_self[3] == frozenset({1, 2, 3})

    assert catalog.substitutes[3] == frozenset({(5, 2)})
    assert catalog.staples == frozenset({7})

    daiquiri = catalog.recipes_by_slug["daiquiri"]
    assert [(group.alt_group, group.ingredient_ids) for group in daiquiri.required_groups] == [
        (None, (3,)),
        (None, (6,)),
        (None, (7,)),
    ]
    assert daiquiri.ingredients[0].amount_ml == 60

    whiskey = catalog.recipes[2]
    assert [(group.alt_group, group.ingredient_ids) for group in whiskey.required_groups] == [
        (1, (8, 9))
    ]
    assert [row.role for row in whiskey.ingredients] == [
        "required",
        "required",
        "optional",
        "garnish",
    ]


def test_cycle_does_not_hang():
    # El seed prohíbe ciclos, pero la estructura debe ser robusta si llegara uno.
    ingredients = [
        Ingredient(1, "a", "A", "generic", parent_id=2),
        Ingredient(2, "b", "B", "generic", parent_id=1),
    ]
    catalog = build_catalog(ingredients, [], [], [])
    assert catalog.ancestors_or_self[1] == frozenset({1, 2})


def test_load_catalog_from_db(engine, tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    shutil.copytree(DATA_DIR, data_dir)
    monkeypatch.setattr(seed, "DATA_DIR", data_dir)
    monkeypatch.setattr(seed, "engine", engine)
    assert seed.main() == 0

    with Session(engine) as session:
        catalog = load_catalog(session)

    ron_blanco = catalog.ingredients_by_slug["ron-blanco"]
    bacardi = catalog.ingredients_by_slug["bacardi-carta-blanca"]
    assert bacardi.parent_id == ron_blanco.id
    assert catalog.ancestors_or_self[bacardi.id] >= {
        ron_blanco.id,
        catalog.ingredients_by_slug["ron"].id,
        catalog.ingredients_by_slug["destilado"].id,
    }

    daiquiri = catalog.recipes_by_slug["daiquiri"]
    assert [group.ingredient_ids for group in daiquiri.required_groups] == [
        (catalog.ingredients_by_slug[slug].id,) for slug in ("ron-blanco", "jugo-de-lima", "azucar")
    ]

    syrup = catalog.ingredients_by_slug["jarabe-simple"]
    sugar = catalog.ingredients_by_slug["azucar"]
    assert (sugar.id, 3) in catalog.substitutes[syrup.id]
    assert sugar.is_staple and catalog.ingredients_by_slug["hielo"].is_staple
