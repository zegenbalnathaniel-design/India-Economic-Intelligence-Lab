import pytest

from econ_lab.modules.micro_price_controls import compute


A, B, C, D = 100.0, 2.0, 10.0, 1.5  # P0 = 90/3.5 = 25.714285714...


def test_binding_ceiling_creates_shortage():
    result = compute(A, B, C, D, control_price=20.0, control_type="ceiling")
    qd = A - B * 20.0  # 60
    qs = C + D * 20.0  # 40
    assert result["binding"] is True
    assert result["qd_at_control"] == pytest.approx(qd)
    assert result["qs_at_control"] == pytest.approx(qs)
    assert result["shortage"] == pytest.approx(qd - qs)
    assert result["shortage"] == pytest.approx(20.0)
    assert result["surplus"] == pytest.approx(0.0)
    assert result["transacted"] == pytest.approx(qs)


def test_binding_floor_creates_surplus():
    result = compute(A, B, C, D, control_price=35.0, control_type="floor")
    qd = A - B * 35.0  # 30
    qs = C + D * 35.0  # 62.5
    assert result["binding"] is True
    assert result["surplus"] == pytest.approx(qs - qd)
    assert result["surplus"] == pytest.approx(32.5)
    assert result["shortage"] == pytest.approx(0.0)
    assert result["transacted"] == pytest.approx(qd)


def test_nonbinding_ceiling_matches_free_market():
    result = compute(A, B, C, D, control_price=30.0, control_type="ceiling")  # P0≈25.71
    assert result["binding"] is False
    assert result["shortage"] == pytest.approx(0.0)
    assert result["surplus"] == pytest.approx(0.0)
    assert result["transacted"] == pytest.approx(result["q0"])


def test_nonbinding_floor_matches_free_market():
    result = compute(A, B, C, D, control_price=20.0, control_type="floor")  # P0≈25.71
    assert result["binding"] is False
    assert result["shortage"] == pytest.approx(0.0)
    assert result["surplus"] == pytest.approx(0.0)


def test_invalid_control_type_raises():
    with pytest.raises(ValueError):
        compute(A, B, C, D, control_price=20.0, control_type="cap")


def test_negative_control_price_raises():
    with pytest.raises(ValueError):
        compute(A, B, C, D, control_price=-5.0, control_type="ceiling")
