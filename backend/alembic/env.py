from alembic import context
from sqlalchemy import create_engine, pool

from app.db import DATABASE_URL
from app.models import Base

config = context.config
target_metadata = Base.metadata
# `sqlalchemy.url` permite apuntar a otra BD desde código (p. ej. las pruebas).
url = config.get_main_option("sqlalchemy.url") or DATABASE_URL


def include_name(name, type_, parent_names) -> bool:
    # Los índices de expresión (0002_busqueda_difusa) se mantienen a mano: autogenerate
    # no puede representarlos en los modelos y propondría borrarlos.
    return not (type_ == "index" and name.endswith(("_trgm", "_normalized")))


def run_migrations_offline() -> None:
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with create_engine(url, poolclass=pool.NullPool).connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, include_name=include_name
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
