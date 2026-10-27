"""Pruebas de `GET /ingredients/tree`: se construye desde el catálogo en memoria, sin BD."""

import pytest
from fastapi.testclient import TestClient

from app.catalog import Ingredient, build_catalog
from app.db import get_catalog
from app.main import app


@pytest.fixture
def tree(catalog):
    def get(catalog=catalog):
        app.dependency_overrides[get_catalog] = lambda: catalog
        return TestClient(app).get("/api/ingredients/tree").json()

    yield get
    app.dependency_overrides.clear()


def _names(nodes):
    return [node["name"] for node in nodes]


def test_tree_shape(tree):
    roots = tree()
    assert _names(roots) == [
        "Azúcar",
        "Crema de cacao",
        "Crema de cacao blanca",
        "Destilados",
        "Hielo",
        "Jarabe simple",
        "Jugo de lima",
        "Licor de café",
        "Menta",
        "Soda",
    ]
    destilados = roots[3]
    assert destilados["kind"] == "category"
    assert _names(destilados["children"]) == ["Ginebra", "Ron", "Whiskey americano"]
    ron = destilados["children"][1]
    assert _names(ron["children"]) == ["Ron añejo", "Ron blanco", "Ron oscuro"]
    assert ron["children"][1]["children"] == [
        {
            "slug": "bacardi-carta-blanca",
            "name": "Bacardí Carta Blanca",
            "kind": "brand",
            "children": [],
        }
    ]


def test_orphan_is_root_and_cycle_does_not_hang(tree):
    catalog = build_catalog(
        [
            Ingredient(1, "a", "A", "generic", parent_id=2),
            Ingredient(2, "b", "B", "generic", parent_id=1),
            Ingredient(3, "huerfano", "Huérfano", "generic", parent_id=99),
        ],
        [],
        [],
        [],
    )
    assert tree(catalog) == [
        {"slug": "huerfano", "name": "Huérfano", "kind": "generic", "children": []}
    ]


def test_tree_in_openapi():
    paths = TestClient(app).get("/openapi.json").json()["paths"]
    assert "/api/ingredients/tree" in paths
