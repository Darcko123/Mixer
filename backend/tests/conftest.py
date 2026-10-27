"""Fixtures de integración con PostgreSQL: requieren `docker compose up -d db`."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, make_url, text

from app.db import DATABASE_URL

TEST_DB = "mixer_test"
TEST_URL = make_url(DATABASE_URL).set(database=TEST_DB)


@pytest.fixture(scope="module")
def alembic_cfg():
    """Crea una BD de pruebas vacía y la lleva a `head`."""
    admin = create_engine(
        make_url(DATABASE_URL).set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)"))
        conn.execute(text(f"CREATE DATABASE {TEST_DB}"))
    admin.dispose()

    cfg = Config(Path(__file__).parents[1] / "alembic.ini")
    url = TEST_URL.render_as_string(hide_password=False)
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(cfg, "head")
    return cfg


@pytest.fixture(scope="module")
def engine(alembic_cfg):
    engine = create_engine(TEST_URL)
    yield engine
    engine.dispose()
