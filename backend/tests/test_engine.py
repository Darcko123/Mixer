"""Pruebas del motor de coincidencias: cobertura, evaluación, ranking y compras sugeridas."""

from itertools import combinations

import pytest

from app.engine import (
    RecipeEvaluation,
    coverage,
    evaluate,
    rank,
    shopping_list,
    suggest_purchases,
)


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
    # Siguen en la receta para mostrarse como informativos.
    assert [row.role for row in result.recipe.ingredients] == [
        "required",
        "required",
        "optional",
        "garnish",
    ]


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
    assert slugs(matches.almost) == [
        "four",
        "two",
        "whiskey",
        "chain",
        "subbed",
        "mojito",
        "gin-tonic",
    ]
    assert [evaluation.missing_count for evaluation in matches.almost] == [1, 1, 1, 1, 1, 2, 2]


def test_rank_max_missing_limits_almost(catalog):
    assert "gin-tonic" not in slugs(rank(catalog, [3, 6], max_missing=1).almost)
    assert rank(catalog, [3, 6], max_missing=0).almost == ()


def test_rank_without_substitutes_treats_them_as_missing(catalog):
    matches = rank(catalog, [3, 6], allow_substitutes=False)

    assert "syrup" not in slugs(matches.can_make)
    # "syrup" pasa a m=1 y "subbed" a m=2, detrás de mojito y gin-tonic (3/5 y 1/3 frente a 0).
    assert slugs(matches.almost) == [
        "four",
        "two",
        "whiskey",
        "chain",
        "syrup",
        "mojito",
        "gin-tonic",
        "subbed",
    ]
    assert all(evaluation.substitute_count == 0 for evaluation in matches.almost)


def plan(purchases) -> list[tuple[int, list[str], list[str]]]:
    return [
        (p.ingredient_id, [r.slug for r in p.unlocks], [r.slug for r in p.improves])
        for p in purchases
    ]


def test_one_purchase_maximizes_unlocks(catalog):
    # Con ron blanco y lima, la menta completa tres recetas y acerca el Mojito.
    assert plan(suggest_purchases(catalog, [3, 6], k=1)) == [
        (11, ["two", "four", "subbed"], ["mojito"])
    ]


def test_one_purchase_breaks_ties_by_partial_progress(catalog):
    # Sin sustitutos: el jarabe simple y el ron completan una receta cada uno, pero el jarabe
    # además acerca "subbed".
    assert plan(suggest_purchases(catalog, [], k=1, allow_substitutes=False)) == [
        (13, ["syrup"], ["subbed"])
    ]


def test_pair_completes_the_most_recipes(catalog):
    # La menta primero (más valor por sí sola). Menta + bourbon, rye o soda completan cuatro
    # recetas y acercan una: el empate entre parejas lo resuelve el slug.
    assert plan(suggest_purchases(catalog, [3, 6], k=2)) == [
        (11, ["two", "four", "subbed"], ["mojito"]),
        (9, ["whiskey"], []),
    ]


@pytest.mark.parametrize("inventory", [[], [3, 6], [4], [11]])
def test_pair_matches_brute_force(catalog, inventory):
    base = len(rank(catalog, inventory).can_make)
    best = max(
        len(rank(catalog, [*inventory, x, y]).can_make) - base
        for x, y in combinations(catalog.ingredients, 2)
    )

    purchases = suggest_purchases(catalog, inventory, k=2)
    assert sum(len(p.unlocks) for p in purchases) == best


def test_greedy_uses_partial_progress(catalog):
    # Ron blanco no completa más que "ron-generic", igual que otros candidatos, pero acerca
    # cuatro recetas; la menta y la lima rematan tres.
    assert plan(suggest_purchases(catalog, [], k=3)) == [
        (3, ["ron-generic"], ["two", "mojito", "daiquiri", "four"]),
        (11, ["two", "subbed"], ["mojito", "four"]),
        (6, ["daiquiri", "four"], ["mojito"]),
    ]


def test_purchase_covers_requirements_through_ancestors(catalog):
    # Comprar ron blanco también cubre una receta que pide "Ron" a secas.
    (purchase,) = suggest_purchases(catalog, [6, 11], k=1)
    assert purchase.ingredient_id == 3
    assert "ron-generic" in [r.slug for r in purchase.unlocks]


def test_no_purchases_when_k_is_zero_or_without_candidates(catalog):
    assert suggest_purchases(catalog, [3, 6], k=0) == ()
    # Al Mojito le falta la soda (m = 1) y al Gin Tonic soda y London Dry (m = 2): con k = 1
    # la London Dry no es candidata.
    assert plan(suggest_purchases(catalog, [3, 6, 11, 9, 20], k=1)) == [
        (12, ["mojito"], ["gin-tonic"])
    ]
    # Todo preparable: no queda nada que comprar.
    assert suggest_purchases(catalog, [3, 6, 11, 9, 20, 12, 15], k=3) == ()


def shopping(items) -> list[tuple[int, int | None, tuple[int, ...], list[str], list[str]]]:
    return [
        (
            item.ingredient_id,
            item.alt_group,
            item.examples,
            [r.slug for r in item.also_unlocks],
            [r.slug for r in item.also_improves],
        )
        for item in items
    ]


def test_shopping_list_with_examples_and_also_unlocks(catalog):
    # Falta el ron blanco: Bacardí como ejemplo; también completa "ron-generic" y acerca tres
    # recetas (sin contar el propio Daiquirí).
    items = shopping_list(catalog, by_slug(catalog, "daiquiri"), [6])

    assert shopping(items) == [(3, None, (4,), ["ron-generic"], ["two", "mojito", "four"])]


def test_shopping_list_lists_each_alternative(catalog):
    items = shopping_list(catalog, by_slug(catalog, "whiskey"), [])

    assert shopping(items) == [(9, 1, (28,), [], []), (10, 1, (), [], [])]


def test_shopping_list_is_empty_when_preparable(catalog):
    assert shopping_list(catalog, by_slug(catalog, "daiquiri"), [3, 6]) == ()
    # Con sustituto también se puede preparar.
    assert shopping_list(catalog, by_slug(catalog, "daiquiri"), [5, 6]) == ()


def test_shopping_list_prefer_original_includes_substitutes(catalog):
    recipe = by_slug(catalog, "daiquiri")

    # El ron añejo ya cubre "ron-generic" y sustituye al blanco en las demás: nada extra.
    assert shopping(shopping_list(catalog, recipe, [5, 6], prefer_original=True)) == [
        (3, None, (4,), [], [])
    ]
    # Sin sustitutos el ron blanco sí acerca las recetas que lo piden.
    assert shopping(shopping_list(catalog, recipe, [5, 6], allow_substitutes=False)) == [
        (3, None, (4,), [], ["two", "mojito", "four"])
    ]


def test_empty_inventory(catalog):
    # Solo se puede preparar lo que cubren los básicos; "Qué comprar" sigue funcionando.
    matches = rank(catalog, [])

    assert slugs(matches.can_make) == ["basics", "syrup"]
    assert plan(suggest_purchases(catalog, [], k=1)) == [
        (11, ["subbed"], ["two", "mojito", "four"])
    ]
    assert shopping(shopping_list(catalog, by_slug(catalog, "daiquiri"), [])) == [
        (3, None, (4,), ["ron-generic"], ["two", "mojito", "four"]),
        (6, None, (), [], ["mojito", "four"]),
    ]


def test_daiquiri_to_mojito_scenario(catalog):
    # Con ron blanco, lima y azúcar (básico) puedo hacer Daiquirí; el Mojito espera menta y soda.
    inventory = [3, 6]
    matches = rank(catalog, inventory)

    assert "daiquiri" in slugs(matches.can_make)
    (mojito,) = (e for e in matches.almost if e.recipe.slug == "mojito")
    assert statuses(mojito) == ["have", "have", "have", "missing", "missing"]

    # La lista de compras del Mojito: la menta además completa otras tres recetas y la soda
    # acerca el Gin Tonic.
    assert shopping(shopping_list(catalog, by_slug(catalog, "mojito"), inventory)) == [
        (11, None, (), ["two", "four", "subbed"], []),
        (12, None, (), [], ["gin-tonic"]),
    ]

    # Si compro menta y soda, desbloqueo el Mojito.
    assert "mojito" in slugs(rank(catalog, [*inventory, 11, 12]).can_make)
