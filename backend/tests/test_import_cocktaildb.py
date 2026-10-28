"""Pruebas de `parse_measure()` (F6.T4) con medidas tal como llegan de TheCocktailDB."""

import pytest

from app.units import UNITS as CATALOG_UNITS
from scripts.import_cocktaildb import UNITS, parse_measure


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Fracciones, mixtos y decimales
        ("1 oz", (1, "oz")),
        ("1/2 oz", (0.5, "oz")),
        ("1 1/2 oz", (1.5, "oz")),
        ("1 2/3 oz", (1.67, "oz")),
        ("0.75 oz", (0.75, "oz")),
        ("1.5 cl", (1.5, "cl")),
        ("4.5 cL", (4.5, "cl")),
        ("4cl", (4, "cl")),
        ("1/8 tsp ground", (0.12, "tsp")),
        # Unidades que se convierten
        ("1 shot", (1.5, "oz")),
        ("1 1/2 shot", (2.25, "oz")),
        ("2 jiggers", (3, "oz")),
        ("2 measures", (3, "oz")),
        ("1/4 cup", (2, "oz")),
        ("2 1/2 cups", (20, "oz")),
        ("1/2 pint", (8, "oz")),
        ("1 qt", (32, "oz")),
        ("1 gal", (128, "oz")),
        ("1 dl", (10, "cl")),
        ("1 L", (1000, "ml")),
        ("1/8 L", (125, "ml")),
        ("1 fifth Smirnoff red label", (750, "ml")),
        ("70ml/2fl oz", (70, "ml")),
        ("1 tblsp", (1, "tbsp")),
        ("2 tbsp", (2, "tbsp")),
        # Plurales y mayúsculas
        ("2 dashes", (2, "dash")),
        ("2 Dashes", (2, "dash")),
        ("3 drops", (3, "gota")),
        ("2 sprigs", (2, "ramita")),
        ("1 Slice", (1, "rodaja")),
        ("2 Wedges", (2, "pieza")),
        ("4 chunks", (4, "pieza")),
        # Sin número
        ("Dash", (1, "dash")),
        ("dash", (1, "dash")),
        # Rangos: se toma el mínimo
        ("2-3 oz", (2, "oz")),
        ("3/4-1 cup", (6, "oz")),
        ("1-2 dash", (1, "dash")),
        ("2 or 3", (2, "pieza")),
        ("4-5 whole green", (4, "pieza")),
        # Adjetivos tras la unidad
        ("2 oz light or dark", (2, "oz")),
        ("1 1/4 cup cold", (10, "oz")),
        ("355 ml frozen", (355, "ml")),
        # Números sin unidad: piezas enteras, fracción como proporción
        ("1", (1, "pieza")),
        ("1 1/2", (1.5, "pieza")),
        ("12", (12, "pieza")),
        ("1/2", (None, None)),
        ("1/3", (None, None)),
        ("2/5", (None, None)),
        ("½", (None, None)),
        # "Juice of": la fracción sí es cantidad de fruta
        ("Juice of 1/2", (0.5, "pieza")),
        ("Juice of 1/4", (0.25, "pieza")),
        ("Juice of 1", (1, "pieza")),
        ("Juice of 1 wedge", (1, "pieza")),
        # Sin volumen fijo o sin cantidad
        ("1 part", (None, None)),
        ("1 1/2 part", (None, None)),
        ("3 parts", (None, None)),
        ("1 splash", (None, None)),
        ("1 pinch", (None, None)),
        ("1 can", (None, None)),
        ("3/4 glass", (None, None)),
        ("1 lb", (None, None)),
        ("60 gr", (None, None)),
        ("2 Fresh leaves", (None, None)),
        ("Top", (None, None)),
        ("Fill with", (None, None)),
        ("Garnish with", (None, None)),
        ("Twist of", (None, None)),
        ("to taste", (None, None)),
        ("cubes", (None, None)),
        (", orange", (None, None)),
        ("", (None, None)),
        (None, (None, None)),
    ],
)
def test_parse_measure(text, expected):
    assert parse_measure(text) == expected


def test_parse_measure_types():
    # El seed exige ml enteros; el resto admite decimales pero no Fraction.
    assert type(parse_measure("1/3 L")[0]) is int
    assert type(parse_measure("1 1/2 oz")[0]) is float
    assert type(parse_measure("2 oz")[0]) is int


def test_units_exist_in_catalog():
    assert {unit for unit, _ in UNITS.values()} <= CATALOG_UNITS
