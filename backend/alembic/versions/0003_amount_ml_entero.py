"""amount_ml como entero

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "recipe_ingredient",
        "amount_ml",
        type_=sa.Integer(),
        existing_type=sa.Numeric(),
        postgresql_using="round(amount_ml)::integer",
    )


def downgrade() -> None:
    op.alter_column(
        "recipe_ingredient", "amount_ml", type_=sa.Numeric(), existing_type=sa.Integer()
    )
