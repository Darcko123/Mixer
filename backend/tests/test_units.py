from decimal import Decimal

from app.units import to_ml


def test_to_ml():
    assert to_ml(60, "ml") == 60
    assert to_ml(Decimal("1.5"), "oz") == 45
    assert to_ml(0.75, "oz") == 22  # 22.5 → 22; en oz se vuelve a mostrar como ¾
    assert to_ml(2, "cl") == 20
    assert to_ml(2, "dash") is None
    assert to_ml(None, "oz") is None
