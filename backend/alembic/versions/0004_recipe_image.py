"""Imagen de receta

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recipe_image",
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("file", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipe.id"],
            name=op.f("fk_recipe_image_recipe_id_recipe"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("recipe_id", name=op.f("pk_recipe_image")),
    )


def downgrade() -> None:
    op.drop_table("recipe_image")
