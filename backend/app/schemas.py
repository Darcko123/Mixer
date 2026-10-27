"""Esquemas Pydantic del contrato de la API (§7).

Las referencias a otros ingredientes o recetas llevan `slug` y `name` para que la UI muestre
"✓ vía Tanqueray" o las recetas desbloqueadas sin pedir nada más. Los parámetros de consulta
son modelos (`Annotated[MatchesQuery, Query()]`) para validar sus rangos aquí: fuera de rango
→ `422`.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.engine import Status

Kind = Literal["category", "generic", "brand"]
Role = Literal["required", "optional", "garnish"]


class IngredientRef(BaseModel):
    slug: str
    name: str


class RecipeRef(BaseModel):
    slug: str
    name: str


# --- Ingredientes e inventario (CU-1) ---


class IngredientSummary(IngredientRef):
    """Resultado del autocompletado y artículo del inventario.

    `path` son los nombres desde la raíz hasta el propio nodo ("Destilado › Ron › Ron blanco").
    """

    kind: Kind
    path: list[str]


class IngredientNode(IngredientRef):
    """Nodo de `GET /ingredients/tree`."""

    kind: Kind
    children: list["IngredientNode"] = []


class InventoryItem(IngredientSummary):
    added_at: datetime


# --- Coincidencias (CU-2, CU-3) ---


class RecipeMatch(RecipeRef):
    """Tarjeta de *Puedo preparar* o *Casi listos*.

    `missing` son los ingredientes de los grupos que faltan; las alternativas de un mismo
    `alt_group` aparecen todas (basta con una).
    """

    popularity: int
    required_count: int
    missing_count: int
    substitute_count: int
    missing: list[IngredientRef]


class MatchesResponse(BaseModel):
    can_make: list[RecipeMatch]
    almost: list[RecipeMatch]


# --- Compras (CU-4a, CU-4b) ---


class PurchaseSuggestion(BaseModel):
    """Compra sugerida, relativa al inventario más las compras anteriores de la lista."""

    ingredient: IngredientRef
    unlocks: list[RecipeRef]
    improves: list[RecipeRef]


class ShoppingItem(BaseModel):
    """Ingrediente a comprar para completar una receta, al nivel del requisito."""

    ingredient: IngredientRef
    alt_group: int | None = None
    examples: list[IngredientRef]
    also_unlocks: list[RecipeRef]
    also_improves: list[RecipeRef]


# --- Recetas (CU-5) ---


class RecipeIngredientStatus(BaseModel):
    """Fila del detalle de una receta.

    `status` es `None` en `optional`/`garnish` (no cuentan para el cálculo) y en las alternativas
    no usadas de un `alt_group` ya cubierto. `covered_by` es el artículo del inventario que lo
    cubre; `substitute`, el sustituto usado en `substitute`.
    """

    ingredient: str
    name: str
    amount: float | None = None
    unit: str | None = None
    amount_ml: int | None = None
    role: Role
    alt_group: int | None = None
    status: Status | None = None
    covered_by: IngredientRef | None = None
    substitute: IngredientRef | None = None


class RecipeDetail(RecipeRef):
    method: str | None = None
    glass: str | None = None
    instructions: str | None = None
    garnish_text: str | None = None
    can_make: bool
    missing_count: int
    substitute_count: int
    ingredients: list[RecipeIngredientStatus]
    shopping_list: list[ShoppingItem]


# --- Parámetros de consulta ---


class SearchQuery(BaseModel):
    q: str = Field(min_length=1)
    limit: int = Field(10, ge=1, le=50)


class MatchesQuery(BaseModel):
    max_missing: int = Field(2, ge=0, le=5)
    allow_substitutes: bool = True


class SuggestionsQuery(BaseModel):
    k: int = Field(3, ge=1, le=5)
    allow_substitutes: bool = True


class RecipeDetailQuery(BaseModel):
    allow_substitutes: bool = True
    # Incluir en la lista de compras también los grupos cubiertos por un sustituto.
    prefer_original: bool = False
