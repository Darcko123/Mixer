"""Pruebas del motor de coincidencias: cobertura, evaluación de grupos y ranking."""

import pytest

from app.catalog import (
    Ingredient,
    RecipeIngredient,
    RecipeMeta,
    Substitute,
    build_catalog,
)
from app.engine import RecipeEvaluation, coverage, evaluate, rank


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
    ]
    return build_catalog(ingredients, substitutes, recipes, recipe_ingredients)


def by_slug(catalog, slug):
    return catalog.recipes_by_slug[slug]


def statuses(evaluation: RecipeEvaluation) -> list[str]:
    return [group.status for group in evaluation.groups]


def test_coverage_includes_ancestors_and_staples(catalog):
    # Tener la marca cubre el genérico, sus ancestros y los básicos asumidos.
    assert coverage(catalog, [4]) == frozenset({1, 2, 3, 4, 7, 8})
    assert coverage(catalog, []) == frozenset({7, 8})
    # Un id ajeno al catálogo no rompe el cálculo.
    assert coverage(catalog, [999]) == frozenset({7, 8})


def test_have_exact_and_staples(catalog):
    result = evaluate(catalog, by_slug(catalog, "daiquiri"), [3, 6])

    assert statuses(result) == ["have", "have", "have"]
    assert result.groups[0].matched_ingredient_id == 3
    assert result.groups[0].covered_by == 3
    # El azúcar es básico: se asume disponible sin estar en el inventario.
    assert result.groups[2].covered_by == 7
    assert result.required_count == 3
    assert result.missing_count == 0
    assert result.substitute_count == 0
    assert result.can_make


def test_have_equivalent_reports_the_inventory_item(catalog):
    result = evaluate(catalog, by_slug(catalog, "daiquiri"), [4, 6])

    assert statuses(result) == ["have_equivalent", "have", "have"]
    assert result.groups[0].matched_ingredient_id == 3
    assert result.groups[0].covered_by == 4
    assert result.can_make


def test_generic_does_not_satisfy_a_specific_requirement(catalog):
    # Tener "Ron" no demuestra que sea ron blanco.
    result = evaluate(catalog, by_slug(catalog, "daiquiri"), [2, 6])

    assert statuses(result) == ["missing", "have", "have"]
    assert result.missing_count == 1
    assert not result.can_make


def test_generic_requirement_is_covered_by_a_brand(catalog):
    result = evaluate(catalog, by_slug(catalog, "ron-generic"), [4])

    assert statuses(result) == ["have_equivalent"]
    assert result.groups[0].matched_ingredient_id == 2
    assert result.groups[0].covered_by == 4


def test_alt_group_uses_any_exact_alternative(catalog):
    result = evaluate(catalog, by_slug(catalog, "whiskey"), [10])

    assert statuses(result) == ["have"]
    assert result.groups[0].group.ingredient_ids == (9, 10)
    assert result.groups[0].matched_ingredient_id == 10
    # Las filas optional/garnish no son requisitos.
    assert result.required_count == 1


def test_alt_group_covered_by_a_brand_of_an_alternative(catalog):
    result = evaluate(catalog, by_slug(catalog, "whiskey"), [28])

    assert statuses(result) == ["have_equivalent"]
    assert result.groups[0].matched_ingredient_id == 9
    assert result.groups[0].covered_by == 28


def test_alt_group_common_ancestor_does_not_satisfy_alternatives(catalog):
    # Tener "Whiskey americano" no demuestra si es bourbon o rye.
    result = evaluate(catalog, by_slug(catalog, "whiskey"), [23])

    assert statuses(result) == ["missing"]


def test_optional_and_garnish_missing_do_not_block(catalog):
    result = evaluate(catalog, by_slug(catalog, "whiskey"), [])

    assert statuses(result) == ["missing"]
    assert result.required_count == 1
    assert result.missing_count == 1


def test_recipe_with_only_staples_is_preparable(catalog):
    result = evaluate(catalog, by_slug(catalog, "basics"), [])

    assert statuses(result) == ["have", "have"]
    assert result.can_make


def test_substitute_is_used_when_covered(catalog):
    result = evaluate(catalog, by_slug(catalog, "daiquiri"), [5, 6])

    assert statuses(result) == ["substitute", "have", "have"]
    assert result.groups[0].matched_ingredient_id == 3
    assert result.groups[0].substitute_id == 5
    assert result.groups[0].covered_by == 5
    assert result.substitute_count == 1
    assert result.missing_count == 0
    assert result.can_make


def test_substitute_covered_by_inheritance(catalog):
    result = evaluate(catalog, by_slug(catalog, "daiquiri"), [24, 6])

    assert statuses(result) == ["substitute", "have", "have"]
    assert result.groups[0].substitute_id == 5
    assert result.groups[0].covered_by == 24


def test_best_quality_substitute_wins(catalog):
    result = evaluate(catalog, by_slug(catalog, "daiquiri"), [5, 27, 6])

    assert result.groups[0].substitute_id == 5  # quality 2 frente a quality 1
    assert result.groups[0].covered_by == 5


def test_substitutes_can_be_disabled(catalog):
    result = evaluate(catalog, by_slug(catalog, "daiquiri"), [5, 6], allow_substitutes=False)

    assert statuses(result) == ["missing", "have", "have"]
    assert result.groups[0].substitute_id is None
    assert result.groups[0].covered_by is None
    assert not result.can_make


def test_substitute_of_a_staple(catalog):
    # El azúcar es básico y sustituye al jarabe simple.
    result = evaluate(catalog, by_slug(catalog, "syrup"), [])

    assert statuses(result) == ["substitute"]
    assert result.groups[0].substitute_id == 7
    assert result.groups[0].covered_by == 7
    assert result.can_make

    strict = evaluate(catalog, by_slug(catalog, "syrup"), [], allow_substitutes=False)
    assert statuses(strict) == ["missing"]


def test_substitutes_are_not_transitive(catalog):
    # A→B y B→C no implican A→C.
    result = evaluate(catalog, by_slug(catalog, "chain"), [22])

    assert statuses(result) == ["missing"]


def test_multiple_coverers_are_deterministic(catalog):
    result = evaluate(catalog, by_slug(catalog, "daiquiri"), [4, 24, 6])

    assert result.groups[0].covered_by == 4


def test_precomputed_coverage_matches(catalog):
    recipe = by_slug(catalog, "daiquiri")
    inventory = [4, 6]
    covered = coverage(catalog, inventory)

    assert evaluate(catalog, recipe, inventory) == evaluate(
        catalog, recipe, inventory, covered=covered
    )


def slugs(evaluations) -> list[str]:
    return [evaluation.recipe.slug for evaluation in evaluations]


def test_rank_can_make_orders_by_substitutes_then_popularity(catalog):
    matches = rank(catalog, [3, 6])

    # Sin sustitutos primero; a igual popularidad desempata el slug.
    assert slugs(matches.can_make) == ["daiquiri", "basics", "ron-generic", "syrup"]
    assert all(evaluation.can_make for evaluation in matches.can_make)


def test_rank_almost_orders_by_missing_substitutes_ratio_popularity(catalog):
    matches = rank(catalog, [3, 6])

    # m=1 sin sustitutos: cobertura relativa (3/4 > 1/2 > 0) antes que popularidad;
    # luego m=1 con sustituto y, al final, m=2 aunque su cobertura relativa sea mayor.
    assert slugs(matches.almost) == ["four", "two", "whiskey", "chain", "subbed", "gin-tonic"]
    assert [evaluation.missing_count for evaluation in matches.almost] == [1, 1, 1, 1, 1, 2]


def test_rank_max_missing_limits_almost(catalog):
    assert "gin-tonic" not in slugs(rank(catalog, [3, 6], max_missing=1).almost)
    assert rank(catalog, [3, 6], max_missing=0).almost == ()


def test_rank_without_substitutes_treats_them_as_missing(catalog):
    matches = rank(catalog, [3, 6], allow_substitutes=False)

    assert "syrup" not in slugs(matches.can_make)
    # "syrup" pasa a m=1 y "subbed" a m=2, detrás de gin-tonic (1/3 frente a 0 de cobertura).
    assert slugs(matches.almost) == [
        "four",
        "two",
        "whiskey",
        "chain",
        "syrup",
        "gin-tonic",
        "subbed",
    ]
    assert all(evaluation.substitute_count == 0 for evaluation in matches.almost)
