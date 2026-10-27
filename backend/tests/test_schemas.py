from decimal import Decimal
from typing import Annotated

import pytest
from fastapi import FastAPI, Query
from fastapi.testclient import TestClient

from app.schemas import IngredientNode, MatchesQuery, RecipeIngredientStatus, SuggestionsQuery


def test_amount_from_catalog_is_a_json_number():
    row = RecipeIngredientStatus(
        ingredient="ron-blanco",
        name="Ron blanco",
        amount=Decimal("60"),
        unit="ml",
        amount_ml=60,
        role="required",
        status="have_equivalent",
        covered_by={"slug": "bacardi-carta-blanca", "name": "Bacardí Carta Blanca"},
    )
    data = row.model_dump(mode="json")
    assert data["amount"] == 60
    assert data["covered_by"]["slug"] == "bacardi-carta-blanca"


def test_tree_nests_nodes():
    tree = IngredientNode.model_validate(
        {
            "slug": "ron",
            "name": "Ron",
            "kind": "generic",
            "children": [{"slug": "ron-blanco", "name": "Ron blanco", "kind": "generic"}],
        }
    )
    assert tree.children[0].children == []


app = FastAPI()


@app.get("/matches")
def matches(params: Annotated[MatchesQuery, Query()]) -> MatchesQuery:
    return params


@app.get("/suggestions")
def suggestions(params: Annotated[SuggestionsQuery, Query()]) -> SuggestionsQuery:
    return params


@pytest.mark.parametrize(
    ("url", "status"),
    [
        ("/matches", 200),
        ("/matches?max_missing=0", 200),
        ("/matches?max_missing=5", 200),
        ("/matches?max_missing=-1", 422),
        ("/matches?max_missing=6", 422),
        ("/suggestions?k=1", 200),
        ("/suggestions?k=5", 200),
        ("/suggestions?k=0", 422),
        ("/suggestions?k=6", 422),
    ],
)
def test_query_ranges(url, status):
    assert TestClient(app).get(url).status_code == status


def test_query_defaults():
    client = TestClient(app)
    assert client.get("/matches").json() == {"max_missing": 2, "allow_substitutes": True}
    assert client.get("/suggestions").json() == {"k": 3, "allow_substitutes": True}
