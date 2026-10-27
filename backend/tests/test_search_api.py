"""Pruebas de la búsqueda difusa `/ingredients?q=` y `/recipes?q=` contra `mixer_test`."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models
from app.db import get_session
from app.main import app


@pytest.fixture
def client(engine):
    with Session(engine) as session:
        session.add_all(
            [
                models.Ingredient(id=1, slug="destilado", name="Destilados", kind="category"),
                models.Ingredient(id=2, slug="ron", name="Ron", kind="generic", parent_id=1),
                models.Ingredient(
                    id=3, slug="ron-blanco", name="Ron blanco", kind="generic", parent_id=2
                ),
                models.Ingredient(id=4, slug="jugo-de-lima", name="Jugo de lima", kind="generic"),
                models.Recipe(id=1, slug="dons-special-daiquiri", name="Don's Special Daiquiri"),
                models.Recipe(id=2, slug="daiquiri", name="Daiquirí"),
                models.Recipe(id=3, slug="margarita", name="Margarita"),
                models.Recipe(id=4, slug="dark-n-stormy", name="Dark 'n' Stormy"),
            ]
        )
        session.flush()
        session.add_all(
            [
                models.IngredientAlias(ingredient_id=3, alias="White rum"),
                models.RecipeAlias(recipe_id=4, alias="Tormenta oscura"),
            ]
        )
        session.commit()

    def session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    client = TestClient(app)
    client.post("/api/catalog/reload")
    yield client
    app.dependency_overrides.clear()
    with Session(engine) as session:
        for model in (models.RecipeAlias, models.Recipe, models.IngredientAlias, models.Ingredient):
            session.query(model).delete()
        session.commit()


def _recipes(client, q, **params):
    return [r["slug"] for r in client.get("/api/recipes", params={"q": q, **params}).json()]


@pytest.mark.parametrize("q", ["daikiri", "DAIQUIRI", "daiquirí"])
def test_daiquiri_comes_first(client, q):
    assert _recipes(client, q)[0] == "daiquiri"


def test_recipe_alias_and_limit(client):
    assert _recipes(client, "tormenta") == ["dark-n-stormy"]
    assert _recipes(client, "daiquiri", limit=1) == ["daiquiri"]
    assert _recipes(client, "xyz") == []


def test_ingredients_prefix_and_alias(client):
    body = client.get("/api/ingredients", params={"q": "ron"}).json()
    assert [i["slug"] for i in body] == ["ron", "ron-blanco"]
    assert body[1]["path"] == ["Destilados", "Ron", "Ron blanco"]
    body = client.get("/api/ingredients", params={"q": "white rum"}).json()
    assert body[0]["slug"] == "ron-blanco"


@pytest.mark.parametrize(
    "url", ["/api/recipes?q=", "/api/ingredients", "/api/ingredients?q=ron&limit=51"]
)
def test_invalid_params_are_422(client, url):
    assert client.get(url).status_code == 422
