"""Pruebas de `/matches`, `/shopping/suggestions` y `/recipes/{slug}` contra `mixer_test`."""

from decimal import Decimal

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
                models.Ingredient(id=1, slug="ron", name="Ron", kind="generic"),
                models.Ingredient(
                    id=2, slug="ron-blanco", name="Ron blanco", kind="generic", parent_id=1
                ),
                models.Ingredient(
                    id=3, slug="bacardi", name="Bacardí Carta Blanca", kind="brand", parent_id=2
                ),
                models.Ingredient(id=4, slug="jugo-de-lima", name="Jugo de lima", kind="generic"),
                models.Ingredient(
                    id=5, slug="azucar", name="Azúcar", kind="generic", is_staple=True
                ),
                models.Ingredient(id=6, slug="menta", name="Menta", kind="generic"),
                models.Ingredient(id=7, slug="soda", name="Soda", kind="generic"),
                models.Ingredient(id=8, slug="bourbon", name="Bourbon", kind="generic"),
                models.Ingredient(id=9, slug="rye", name="Rye", kind="generic"),
                models.Recipe(
                    id=1, slug="daiquiri", name="Daiquirí", method="shake", popularity=85
                ),
                models.Recipe(id=2, slug="mojito", name="Mojito", popularity=90),
                models.Recipe(id=3, slug="whiskey", name="Whiskey"),
            ]
        )
        session.flush()
        session.add_all(
            [
                models.RecipeIngredient(
                    recipe_id=1,
                    ingredient_id=2,
                    position=1,
                    amount=Decimal(60),
                    unit="ml",
                    amount_ml=60,
                ),
                models.RecipeIngredient(recipe_id=1, ingredient_id=4, position=2),
                models.RecipeIngredient(recipe_id=1, ingredient_id=5, position=3),
                models.RecipeIngredient(recipe_id=2, ingredient_id=2, position=1),
                models.RecipeIngredient(recipe_id=2, ingredient_id=4, position=2),
                models.RecipeIngredient(recipe_id=2, ingredient_id=6, position=3),
                models.RecipeIngredient(recipe_id=2, ingredient_id=7, position=4),
                models.RecipeIngredient(recipe_id=3, ingredient_id=8, position=1, alt_group=1),
                models.RecipeIngredient(recipe_id=3, ingredient_id=9, position=2, alt_group=1),
                models.InventoryItem(ingredient_id=3),
                models.InventoryItem(ingredient_id=4),
                models.InventoryItem(ingredient_id=9),
                models.RecipeImage(
                    recipe_id=1,
                    file="daiquiri.webp",
                    source_url="https://iba-world.com/iba-cocktail/daiquiri/",
                ),
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
        for model in (
            models.InventoryItem,
            models.RecipeIngredient,
            models.Recipe,
            models.Ingredient,
        ):
            session.query(model).delete()
        session.commit()


def test_matches(client):
    body = client.get("/api/matches").json()
    assert [r["slug"] for r in body["can_make"]] == ["daiquiri", "whiskey"]
    assert [(r["slug"], r["missing"]) for r in body["almost"]] == [
        ("mojito", [{"slug": "menta", "name": "Menta"}, {"slug": "soda", "name": "Soda"}])
    ]
    assert client.get("/api/matches?max_missing=1").json()["almost"] == []


def test_suggestions(client):
    body = client.get("/api/shopping/suggestions?k=2").json()
    assert [s["ingredient"]["slug"] for s in body] == ["menta", "soda"]
    assert body[1]["unlocks"] == [{"slug": "mojito", "name": "Mojito"}]


def test_recipe_detail(client):
    body = client.get("/api/recipes/daiquiri").json()
    assert body["can_make"] and body["method"] == "shake" and body["shopping_list"] == []
    rum, lime, sugar = body["ingredients"]
    assert rum["status"] == "have_equivalent" and rum["amount"] == 60
    assert rum["covered_by"] == {"slug": "bacardi", "name": "Bacardí Carta Blanca"}
    assert lime["status"] == sugar["status"] == "have"

    mojito = client.get("/api/recipes/mojito").json()
    assert mojito["missing_count"] == 2
    assert [s["ingredient"]["slug"] for s in mojito["shopping_list"]] == ["menta", "soda"]


DAIQUIRI_IMAGE = {
    "url": "/api/images/daiquiri.webp",
    "source_url": "https://iba-world.com/iba-cocktail/daiquiri/",
}


def test_recipe_image(client):
    assert client.get("/api/recipes/daiquiri").json()["image"] == DAIQUIRI_IMAGE
    assert client.get("/api/recipes/mojito").json()["image"] is None

    body = client.get("/api/matches").json()
    images = {r["slug"]: r["image"] for r in body["can_make"] + body["almost"]}
    assert images == {"daiquiri": DAIQUIRI_IMAGE, "whiskey": None, "mojito": None}

    # La API sirve el archivo: el navegador no depende de iba-world.com.
    image = client.get(DAIQUIRI_IMAGE["url"])
    assert image.status_code == 200 and image.headers["content-type"] == "image/webp"
    assert client.get("/api/images/no-existe.webp").status_code == 404


def test_unused_alternative_has_no_status(client):
    bourbon, rye = client.get("/api/recipes/whiskey").json()["ingredients"]
    assert bourbon["status"] is None and rye["status"] == "have"


def test_unknown_recipe_is_404(client):
    assert client.get("/api/recipes/no-existe").status_code == 404


@pytest.mark.parametrize(
    "url",
    [
        "/api/matches?max_missing=-1",
        "/api/matches?max_missing=6",
        "/api/shopping/suggestions?k=0",
        "/api/shopping/suggestions?k=6",
    ],
)
def test_out_of_range_is_422(client, url):
    assert client.get(url).status_code == 422


def test_reload_and_health(client):
    summary = {"ingredients": 9, "recipes": 3}
    assert client.post("/api/catalog/reload").json() == summary
    assert client.get("/api/health").json() == {"status": "ok", "catalog": summary}
