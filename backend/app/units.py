from decimal import Decimal

# Unidades de volumen convertibles (1 oz = 30 ml, convención de coctelería). Las de barra
# (dash, barspoon…) y de pieza no se convierten: se muestran con su cantidad y unidad.
ML_PER_UNIT = {"ml": 1, "cl": 10, "oz": 30}
UNITS = {
    *ML_PER_UNIT,
    "dash",
    "barspoon",
    "tsp",
    "tbsp",
    "gota",
    "pieza",
    "hoja",
    "rodaja",
    "ramita",
}


def to_ml(amount: Decimal | float | None, unit: str | None) -> int | None:
    """Cantidad original → ml enteros, o None si la unidad no es de volumen."""
    if amount is None or unit not in ML_PER_UNIT:
        return None
    return round(Decimal(str(amount)) * ML_PER_UNIT[unit])
