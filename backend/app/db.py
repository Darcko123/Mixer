import os

from sqlalchemy import create_engine

# Por defecto apunta al servicio `db` de docker-compose.yml.
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://mixer:mixer@localhost:5432/mixer"
)

engine = create_engine(DATABASE_URL)
