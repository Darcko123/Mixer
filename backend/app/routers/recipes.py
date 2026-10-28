"""Coincidencias, compras sugeridas y detalle de receta (CU-2 a CU-5), delegando en el motor."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app import engine, models, schemas
from app.catalog import Catalog, Recipe
from app.db import CatalogDep, SessionDep
from app.search import fuzzy_ids

router = APIRouter()

# Donde app.main monta data/images/.
IMAGES_URL = "/api/images/"


def _inventory(session: SessionDep) -> frozenset[int]:
    return frozenset(session.scalars(select(models.InventoryItem.ingredient_id)))


InventoryDep = Annotated[frozenset[int], Depends(_inventory)]


def _ingredient(catalog: Catalog, ingredient_id: int) -> schemas.IngredientRef:
    ingredient = catalog.ingredients[ingredient_id]
    return schemas.IngredientRef(slug=ingredient.slug, name=ingredient.name)


def _recipes(recipes: tuple[Recipe, ...]) -> list[schemas.RecipeRef]:
    return [schemas.RecipeRef(slug=r.slug, name=r.name) for r in recipes]


def _image(recipe: Recipe) -> schemas.RecipeImage | None:
    if recipe.image is None:
        return None
    return schemas.RecipeImage(
        url=IMAGES_URL + recipe.image.file, source_url=recipe.image.source_url
    )


def _match(catalog: Catalog, result: engine.RecipeEvaluation) -> schemas.RecipeMatch:
    return schemas.RecipeMatch(
        slug=result.recipe.slug,
        name=result.recipe.name,
        popularity=result.recipe.popularity,
        required_count=result.required_count,
        missing_count=result.missing_count,
        substitute_count=result.substitute_count,
        missing=[
            _ingredient(catalog, ingredient_id)
            for group in result.groups
            if group.status == "missing"
            for ingredient_id in group.group.ingredient_ids
        ],
        image=_image(result.recipe),
        flavors=list(result.recipe.flavors),
    )


@router.get("/matches", tags=["matches"])
def matches(
    params: Annotated[schemas.MatchesQuery, Query()],
    catalog: CatalogDep,
    inventory: InventoryDep,
) -> schemas.MatchesResponse:
    """*Puedo preparar* y *Casi listos* (hasta `max_missing` faltantes), ya ordenados."""
    result = engine.rank(
        catalog,
        inventory,
        max_missing=params.max_missing,
        allow_substitutes=params.allow_substitutes,
    )
    return schemas.MatchesResponse(
        can_make=[_match(catalog, r) for r in result.can_make],
        almost=[_match(catalog, r) for r in result.almost],
    )


@router.get("/shopping/suggestions", tags=["shopping"])
def shopping_suggestions(
    params: Annotated[schemas.SuggestionsQuery, Query()],
    catalog: CatalogDep,
    inventory: InventoryDep,
) -> list[schemas.PurchaseSuggestion]:
    """Hasta `k` compras, en el orden en que conviene hacerlas."""
    purchases = engine.suggest_purchases(
        catalog, inventory, params.k, allow_substitutes=params.allow_substitutes
    )
    return [
        schemas.PurchaseSuggestion(
            ingredient=_ingredient(catalog, p.ingredient_id),
            unlocks=_recipes(p.unlocks),
            improves=_recipes(p.improves),
        )
        for p in purchases
    ]


@router.get("/recipes", tags=["recipes"])
def search_recipes(
    params: Annotated[schemas.SearchQuery, Query()], session: SessionDep
) -> list[schemas.RecipeRef]:
    """Búsqueda difusa por nombre y alias (modo búsqueda, CU-5)."""
    ids = fuzzy_ids(
        session,
        [
            (models.Recipe.id, models.Recipe.name),
            (models.RecipeAlias.recipe_id, models.RecipeAlias.alias),
        ],
        params.q,
        params.limit,
    )
    rows = {
        r.id: r for r in session.scalars(select(models.Recipe).where(models.Recipe.id.in_(ids)))
    }
    return [schemas.RecipeRef(slug=rows[i].slug, name=rows[i].name) for i in ids]


@router.get("/recipes/{slug}", tags=["recipes"])
def recipe_detail(
    slug: str,
    params: Annotated[schemas.RecipeDetailQuery, Query()],
    catalog: CatalogDep,
    inventory: InventoryDep,
    session: SessionDep,
) -> schemas.RecipeDetail:
    """Receta con el estado de cada ingrediente frente al inventario y su lista de compras."""
    recipe = catalog.recipes_by_slug.get(slug)
    if recipe is None:
        raise HTTPException(404, f"Receta desconocida: {slug}")
    # Método, vaso e instrucciones no están en el catálogo en memoria.
    row = session.get_one(models.Recipe, recipe.id)
    evaluation = engine.evaluate(
        catalog, recipe, inventory, allow_substitutes=params.allow_substitutes
    )
    groups = {
        ingredient_id: group
        for group in evaluation.groups
        for ingredient_id in group.group.ingredient_ids
    }

    ingredients = []
    for item in recipe.ingredients:
        group = groups.get(item.ingredient_id) if item.role == "required" else None
        # Una alternativa no usada de un grupo ya cubierto no tiene estado propio.
        used = group is not None and (
            group.status == "missing" or group.matched_ingredient_id == item.ingredient_id
        )
        ingredient = catalog.ingredients[item.ingredient_id]
        ingredients.append(
            schemas.RecipeIngredientStatus(
                ingredient=ingredient.slug,
                name=ingredient.name,
                amount=item.amount,
                unit=item.unit,
                amount_ml=item.amount_ml,
                role=item.role,
                alt_group=item.alt_group,
                status=group.status if used else None,
                covered_by=_ingredient(catalog, group.covered_by)
                if used and group.covered_by is not None
                else None,
                substitute=_ingredient(catalog, group.substitute_id)
                if used and group.substitute_id is not None
                else None,
            )
        )

    shopping = engine.shopping_list(
        catalog,
        recipe,
        inventory,
        allow_substitutes=params.allow_substitutes,
        prefer_original=params.prefer_original,
    )
    return schemas.RecipeDetail(
        slug=recipe.slug,
        name=recipe.name,
        method=row.method,
        glass=row.glass,
        instructions=row.instructions,
        garnish_text=row.garnish_text,
        image=_image(recipe),
        flavors=list(recipe.flavors),
        can_make=evaluation.can_make,
        missing_count=evaluation.missing_count,
        substitute_count=evaluation.substitute_count,
        ingredients=ingredients,
        shopping_list=[
            schemas.ShoppingItem(
                ingredient=_ingredient(catalog, s.ingredient_id),
                alt_group=s.alt_group,
                examples=[_ingredient(catalog, e) for e in s.examples],
                also_unlocks=_recipes(s.also_unlocks),
                also_improves=_recipes(s.also_improves),
            )
            for s in shopping
        ],
    )
