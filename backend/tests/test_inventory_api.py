"""Pruebas de los endpoints de inventario contra `mixer_test`."""

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
        session.query(models.InventoryItem).delete()
        session.query(models.Ingredient).delete()
        session.commit()


def test_put_is_idempotent(client):
    first = client.put("/api/inventory/ron-blanco")
    assert first.status_code == 200
    assert first.json()["path"] == ["Destilados", "Ron", "Ron blanco"]

    second = client.put("/api/inventory/ron-blanco")
    assert second.status_code == 200
    assert second.json() == first.json()
    assert [item["slug"] for item in client.get("/api/inventory").json()] == ["ron-blanco"]


def test_list_is_ordered_by_path(client):
    assert client.get("/api/inventory").json() == []
    client.put("/api/inventory/ron-blanco")
    client.put("/api/inventory/jugo-de-lima")
    assert [item["slug"] for item in client.get("/api/inventory").json()] == [
        "ron-blanco",
        "jugo-de-lima",
    ]


def test_delete(client):
    client.put("/api/inventory/ron")
    assert client.delete("/api/inventory/ron").status_code == 204
    assert client.get("/api/inventory").json() == []
    # Quitar algo que ya no está sigue siendo un éxito.
    assert client.delete("/api/inventory/ron").status_code == 204


@pytest.mark.parametrize("method", ["put", "delete"])
def test_unknown_slug_is_404(client, method):
    assert getattr(client, method)("/api/inventory/no-existe").status_code == 404


def test_category_cannot_be_added(client):
    assert client.put("/api/inventory/destilado").status_code == 422
    assert client.get("/api/inventory").json() == []
