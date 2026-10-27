"""Pruebas de punta a punta de la API: el catálogo de `conftest.py` se escribe en `mixer_test`,
se recarga y se recorren los casos de uso a través de los endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models
from app.db import get_session
from app.main import app


@pytest.fixture
def client(engine, catalog):
    with Session(engine) as session:
        # Padres antes que hijos por la FK de `parent_id`.
        session.add_all(
            models.Ingredient(
                id=i.id,
                slug=i.slug,
                name=i.name,
                kind=i.kind,
                parent_id=i.parent_id,
                is_staple=i.is_staple,
            )
            for i in sorted(catalog.ingredients.values(), key=lambda i: len(catalog.paths[i.id]))
        )
        for r in catalog.recipes.values():
            session.add(models.Recipe(id=r.id, slug=r.slug, name=r.name, popularity=r.popularity))
        session.flush()
        session.add_all(
            models.IngredientSubstitute(ingredient_id=i, substitute_id=s, quality=q)
            for i, subs in catalog.substitutes.items()
            for s, q in subs
        )
        session.add_all(
            models.RecipeIngredient(
                recipe_id=row.recipe_id,
                ingredient_id=row.ingredient_id,
                position=row.position,
                role=row.role,
                alt_group=row.alt_group,
            )
            for r in catalog.recipes.values()
            for row in r.ingredients
        )
        session.commit()

    def session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    client = TestClient(app)
    assert client.post("/api/catalog/reload").json() == {
        "ingredients": len(catalog.ingredients),
        "recipes": len(catalog.recipes),
    }
    yield client
    app.dependency_overrides.clear()
    with Session(engine) as session:
        for model in (
            models.InventoryItem,
            models.RecipeIngredient,
            models.IngredientSubstitute,
            models.Recipe,
            models.Ingredient,
        ):
            session.query(model).delete()
        session.commit()


def _slugs(items):
    return [item["slug"] for item in items]


def _have(client, *slugs):
    for slug in slugs:
        assert client.put(f"/api/inventory/{slug}").status_code == 200


def test_daiquiri_to_mojito_scenario(client):
    _have(client, "ron-blanco", "jugo-de-lima")
    matches = client.get("/api/matches").json()
    assert "daiquiri" in _slugs(matches["can_make"])
    (mojito,) = (r for r in matches["almost"] if r["slug"] == "mojito")
    assert _slugs(mojito["missing"]) == ["menta", "soda"]

    # La menta además completa otras tres recetas y la soda acerca el Gin Tonic.
    shopping = client.get("/api/recipes/mojito").json()["shopping_list"]
    assert [
        (s["ingredient"]["slug"], _slugs(s["also_unlocks"]), _slugs(s["also_improves"]))
        for s in shopping
    ] == [("menta", ["two", "four", "subbed"], []), ("soda", [], ["gin-tonic"])]

    (first,) = client.get("/api/shopping/suggestions?k=1").json()
    assert first["ingredient"]["slug"] == "menta"
    assert _slugs(first["unlocks"]) == ["two", "four", "subbed"]

    _have(client, "menta", "soda")
    assert "mojito" in _slugs(client.get("/api/matches").json()["can_make"])

    # Quitar la menta lo devuelve a *Casi listos*.
    assert client.delete("/api/inventory/menta").status_code == 204
    matches = client.get("/api/matches").json()
    assert "mojito" not in _slugs(matches["can_make"])
    assert "mojito" in _slugs(matches["almost"])


def test_substitutes(client):
    _have(client, "ron-anejo", "jugo-de-lima")
    body = client.get("/api/recipes/daiquiri").json()
    assert body["can_make"] and body["substitute_count"] == 1
    rum = body["ingredients"][0]
    assert rum["status"] == "substitute"
    assert rum["substitute"] == rum["covered_by"] == {"slug": "ron-anejo", "name": "Ron añejo"}

    strict = client.get("/api/recipes/daiquiri?allow_substitutes=false").json()
    assert not strict["can_make"] and strict["ingredients"][0]["status"] == "missing"
    assert "daiquiri" not in _slugs(
        client.get("/api/matches?allow_substitutes=false").json()["can_make"]
    )

    (item,) = client.get("/api/recipes/daiquiri?prefer_original=true").json()["shopping_list"]
    assert item["ingredient"]["slug"] == "ron-blanco"
    assert _slugs(item["examples"]) == ["bacardi-carta-blanca"]


def test_empty_inventory(client):
    assert client.get("/api/inventory").json() == []
    assert _slugs(client.get("/api/matches").json()["can_make"]) == ["basics", "syrup"]
    (first,) = client.get("/api/shopping/suggestions?k=1").json()
    assert first["ingredient"]["slug"] == "menta"
    assert _slugs(first["unlocks"]) == ["subbed"]
    assert _slugs(first["improves"]) == ["two", "mojito", "four"]


@pytest.mark.parametrize(
    "url",
    [
        "/api/recipes?q=dai&limit=0",
        "/api/ingredients?q=",
        "/api/matches?allow_substitutes=quizá",
        "/api/recipes/daiquiri?prefer_original=quizá",
    ],
)
def test_invalid_params_are_422(client, url):
    assert client.get(url).status_code == 422


def test_docs_list_every_endpoint():
    client = TestClient(app)
    assert client.get("/docs").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    for path, methods in {
        "/api/ingredients": {"get"},
        "/api/ingredients/tree": {"get"},
        "/api/inventory": {"get"},
        "/api/inventory/{slug}": {"put", "delete"},
        "/api/matches": {"get"},
        "/api/shopping/suggestions": {"get"},
        "/api/recipes": {"get"},
        "/api/recipes/{slug}": {"get"},
        "/api/health": {"get"},
    }.items():
        assert methods <= paths[path].keys(), path
