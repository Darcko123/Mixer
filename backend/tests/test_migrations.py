"""Integración con PostgreSQL: requiere `docker compose up -d db`."""

import pytest
from alembic import command
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Ingredient, IngredientAlias, Recipe, RecipeIngredient


def test_downgrade_and_upgrade_again(alembic_cfg, engine):
    command.downgrade(alembic_cfg, "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]
    command.upgrade(alembic_cfg, "head")
    assert "recipe_ingredient" in inspect(engine).get_table_names()


def test_constraints(engine):
    with Session(engine) as s:
        rum = Ingredient(slug="ron-blanco", name="Ron blanco", kind="generic")
        recipe = Recipe(slug="daiquiri", name="Daiquirí")
        s.add_all([rum, recipe])
        s.flush()
        s.add_all(
            [
                RecipeIngredient(recipe_id=recipe.id, ingredient_id=rum.id, position=1),
                IngredientAlias(ingredient_id=rum.id, alias="Ron plata"),
            ]
        )
        s.flush()

        rejected = [
            RecipeIngredient(recipe_id=recipe.id, ingredient_id=rum.id, role="x", position=2),
            RecipeIngredient(recipe_id=recipe.id, ingredient_id=999_999, position=2),
            Ingredient(slug="ron", name="Ron", kind="bebida"),
            # Duplicado tras normalizar mayúsculas y acentos.
            IngredientAlias(ingredient_id=rum.id, alias="RON PLATÁ"),
        ]
        for row in rejected:
            with pytest.raises(IntegrityError), s.begin_nested():
                s.add(row)
                s.flush()

        s.delete(recipe)
        s.flush()
        assert s.scalar(select(func.count()).select_from(RecipeIngredient)) == 0


def test_fuzzy_search_uses_trigram_index(engine):
    sql = "SELECT name FROM recipe WHERE immutable_unaccent(lower(name)) % 'daiquiri'"
    with engine.connect() as conn:
        conn.execute(text("INSERT INTO recipe (slug, name) VALUES ('daiquiri', 'Daiquirí')"))
        # Con una tabla diminuta el planificador prefiere seq scan; se desactiva para
        # comprobar que el índice es aplicable a la expresión.
        conn.execute(text("SET LOCAL enable_seqscan = off"))
        plan = "\n".join(conn.execute(text(f"EXPLAIN {sql}")).scalars())
        assert "ix_recipe_name_trgm" in plan
        assert conn.execute(text(sql)).scalars().all() == ["Daiquirí"]
