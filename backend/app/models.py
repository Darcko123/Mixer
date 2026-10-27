from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    MetaData,
    Numeric,
    SmallInteger,
    Text,
    false,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Nombres deterministas de constraints para que las migraciones sean reproducibles.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {str: Text}


class Ingredient(Base):
    __tablename__ = "ingredient"
    __table_args__ = (CheckConstraint("kind IN ('category', 'generic', 'brand')", name="kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    # Ciclos prohibidos: los valida el seed.
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("ingredient.id"))
    kind: Mapped[str]
    is_staple: Mapped[bool] = mapped_column(default=False, server_default=false())
    abv: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))


class IngredientAlias(Base):
    # Índice único sobre immutable_unaccent(lower(alias)) en la migración de búsqueda.
    __tablename__ = "ingredient_alias"

    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredient.id", ondelete="CASCADE"), primary_key=True
    )
    alias: Mapped[str] = mapped_column(primary_key=True)


class IngredientSubstitute(Base):
    """Dirigida: `substitute_id` puede reemplazar a `ingredient_id`."""

    __tablename__ = "ingredient_substitute"
    __table_args__ = (
        CheckConstraint("quality BETWEEN 1 AND 3", name="quality"),
        CheckConstraint("ingredient_id <> substitute_id", name="not_self"),
    )

    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredient.id", ondelete="CASCADE"), primary_key=True
    )
    substitute_id: Mapped[int] = mapped_column(
        ForeignKey("ingredient.id", ondelete="CASCADE"), primary_key=True
    )
    quality: Mapped[int] = mapped_column(SmallInteger)
    note: Mapped[str | None]


class Recipe(Base):
    __tablename__ = "recipe"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    method: Mapped[str | None]
    glass: Mapped[str | None]
    instructions: Mapped[str | None]
    garnish_text: Mapped[str | None]
    source: Mapped[str | None]
    popularity: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")


class RecipeAlias(Base):
    __tablename__ = "recipe_alias"

    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipe.id", ondelete="CASCADE"), primary_key=True
    )
    alias: Mapped[str] = mapped_column(primary_key=True)


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredient"
    __table_args__ = (CheckConstraint("role IN ('required', 'optional', 'garnish')", name="role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id", ondelete="CASCADE"), index=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredient.id"), index=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric)
    unit: Mapped[str | None]
    # Volumen en ml enteros (solo ml/cl/oz, ver app.units); la UI lo muestra en ml u oz.
    amount_ml: Mapped[int | None]
    role: Mapped[str] = mapped_column(default="required", server_default="required")
    # Filas de la misma receta con el mismo valor = alternativas ("bourbon o rye").
    alt_group: Mapped[int | None] = mapped_column(SmallInteger)
    position: Mapped[int] = mapped_column(SmallInteger)


class InventoryItem(Base):
    # Sin ON DELETE CASCADE: borrar un ingrediente del inventario debe fallar, no perder datos.
    __tablename__ = "inventory_item"

    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredient.id"), primary_key=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
