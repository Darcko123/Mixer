"""Perfil de sabor de receta

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FLAVORS = (
    "sweet",
    "sour",
    "bitter",
    "dry",
    "strong",
    "creamy",
    "fruity",
    "herbal",
    "spicy",
    "savory",
)


def upgrade() -> None:
    op.add_column(
        "recipe",
        sa.Column("flavors", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_recipe_flavors"),
        "recipe",
        f"flavors <@ ARRAY[{', '.join(f"'{f}'" for f in FLAVORS)}]::text[]",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_recipe_flavors"), "recipe", type_="check")
    op.drop_column("recipe", "flavors")
