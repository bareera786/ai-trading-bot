import pytest

pytest.importorskip("flask_mail")

from app.services.trading import _default_safe_float


def test_default_safe_float():
    assert _default_safe_float(None) == 0.0
    assert _default_safe_float("3.14") == 3.14
    assert _default_safe_float("bad", default=7.5) == 7.5
    assert _default_safe_float(5) == 5.0
