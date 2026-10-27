"""Rendimiento del motor con un catálogo sintético de 1 000 recetas (umbral: 100 ms)."""

import random
from time import perf_counter

import pytest

from app.catalog import Ingredient, RecipeIngredient, RecipeMeta, Substitute, build_catalog
from app.engine import rank, suggest_purchases

THRESHOLD_S = 0.1


def synthetic_catalog(seed: int = 7):
    """Taxonomía categoría → genérico → específico → marca, sustitutos y recetas al azar.

    ~500 ingredientes: 10 categorías × 5 genéricos × 2 específicos × 3 marcas, 40 genéricos
    sueltos (jugos, jarabes…) y 3 básicos. Las recetas usan genéricos y específicos, con
    algún `alt_group` y filas `optional`/`garnish`, como en el catálogo real.
    """
    rng = random.Random(seed)
    ingredients: list[Ingredient] = []

    def add(kind: str, parent_id: int | None = None, is_staple: bool = False) -> int:
        ingredient_id = len(ingredients) + 1
        slug = f"{kind}-{ingredient_id}"
        ingredients.append(Ingredient(ingredient_id, slug, slug, kind, parent_id, is_staple))
        return ingredient_id

    requirable: list[int] = []
    brands: list[int] = []
    for _ in range(10):
        category = add("category")
        for _ in range(5):
            generic = add("generic", category)
            requirable.append(generic)
            for _ in range(2):
                specific = add("generic", generic)
                requirable.append(specific)
                brands.extend(add("brand", specific) for _ in range(3))
    requirable.extend(add("generic") for _ in range(40))
    staples = [add("generic", is_staple=True) for _ in range(3)]

    substitutes = [
        Substitute(a, b, rng.randint(1, 3))
        for a, b in {tuple(rng.sample(requirable, 2)) for _ in range(150)}
    ]

    recipes: list[RecipeMeta] = []
    rows: list[RecipeIngredient] = []
    for recipe_id in range(1, 1001):
        recipes.append(RecipeMeta(recipe_id, f"r-{recipe_id:04}", f"R {recipe_id}"))
        picked = rng.sample(requirable, rng.randint(2, 6))
        if rng.random() < 0.3:
            picked.append(rng.choice(staples))
        position = 0
        for ingredient_id in picked:
            position += 1
            rows.append(RecipeIngredient(recipe_id, ingredient_id, position))
        if rng.random() < 0.2:  # "X o Y"
            for ingredient_id in rng.sample(requirable, 2):
                position += 1
                rows.append(RecipeIngredient(recipe_id, ingredient_id, position, alt_group=1))
        for role in ("optional", "garnish"):
            if rng.random() < 0.3:
                position += 1
                rows.append(RecipeIngredient(recipe_id, rng.choice(requirable), position, role))

    catalog = build_catalog(ingredients, substitutes, recipes, rows)
    inventory = rng.sample(brands, 25) + rng.sample(requirable, 15)
    return catalog, inventory


def best_time(fn, repeat: int = 5) -> float:
    """Mejor de `repeat` ejecuciones: descarta el ruido del sistema."""
    times = []
    for _ in range(repeat):
        start = perf_counter()
        fn()
        times.append(perf_counter() - start)
    return min(times)


@pytest.fixture(scope="module")
def synthetic():
    return synthetic_catalog()


def test_synthetic_catalog_is_realistic(synthetic):
    catalog, inventory = synthetic
    matches = rank(catalog, inventory)

    assert len(catalog.recipes) == 1000
    # Que haya trabajo real: recetas preparables, casi listas y compras con efecto.
    assert matches.can_make and len(matches.almost) >= 50
    assert len(suggest_purchases(catalog, inventory, k=3)) == 3


def test_rank_under_threshold(synthetic):
    catalog, inventory = synthetic
    assert best_time(lambda: rank(catalog, inventory)) < THRESHOLD_S


def test_suggest_purchases_k3_under_threshold(synthetic):
    catalog, inventory = synthetic
    assert best_time(lambda: suggest_purchases(catalog, inventory, k=3)) < THRESHOLD_S
