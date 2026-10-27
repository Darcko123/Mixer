"""búsqueda difusa: pg_trgm, unaccent e índices de trigramas

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-26

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (tabla, columna) indexadas para búsqueda difusa.
TRGM_COLUMNS = [
    ("recipe", "name"),
    ("recipe_alias", "alias"),
    ("ingredient", "name"),
    ("ingredient_alias", "alias"),
]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    # unaccent() es STABLE (depende de search_path); el diccionario cualificado lo hace
    # seguro de declarar IMMUTABLE y usar en índices.
    op.execute(
        """
        CREATE FUNCTION immutable_unaccent(text) RETURNS text
        LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
        AS $$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$
        """
    )
    for table, column in TRGM_COLUMNS:
        op.execute(
            f"CREATE INDEX ix_{table}_{column}_trgm ON {table} "
            f"USING gin (immutable_unaccent(lower({column})) gin_trgm_ops)"
        )
    op.execute(
        "CREATE UNIQUE INDEX uq_ingredient_alias_normalized "
        "ON ingredient_alias (immutable_unaccent(lower(alias)))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX uq_ingredient_alias_normalized")
    for table, column in TRGM_COLUMNS:
        op.execute(f"DROP INDEX ix_{table}_{column}_trgm")
    op.execute("DROP FUNCTION immutable_unaccent(text)")
    op.execute("DROP EXTENSION unaccent")
    op.execute("DROP EXTENSION pg_trgm")
