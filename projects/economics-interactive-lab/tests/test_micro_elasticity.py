import pytest

from econ_lab.modules.micro_elasticity import compute


def test_point_elasticity_matches_exact_formula():
    # Q = 100 - 2P, evaluate at P=20 -> Q=60, PED = -b*(P/Q) = -2*(20/60)
    a, b, price = 100.0, 2.0, 20.0
    result = compute(a, b, price)
    q = a - b * price
    expected = -b * (price / q)
    assert result["quantity"] == pytest.approx(q)
    assert result["elasticity"] == pytest.approx(expected)
    assert result["elasticity"] == pytest.approx(-2 * (20 / 60))


def test_elasticity_label_boundaries():
    # Unit elastic exactly when |PED| == 1, i.e. b*P/Q == 1 i.e. b*P == a-b*P
    # For Q = a - bP: unit elastic at P = a/(2b).
    a, b = 100.0, 2.0
    p_unit = a / (2 * b)
    result = compute(a, b, p_unit)
    assert result["elasticity"] == pytest.approx(-1.0)
    assert result["label"] == "unit elastic"

    result_inelastic = compute(a, b, price=1.0)  # near P=0 -> inelastic
    assert abs(result_inelastic["elasticity"]) < 1
    assert result_inelastic["label"] == "inelastic"

    result_elastic = compute(a, b, price=p_unit + 10.0)
    assert abs(result_elastic["elasticity"]) > 1
    assert result_elastic["label"] == "elastic"


def test_zero_price_gives_zero_elasticity():
    result = compute(a=100.0, b=2.0, price=0.0)
    assert result["elasticity"] == pytest.approx(0.0)
    assert result["label"] == "inelastic"


def test_price_at_choke_price_raises():
    # Q = a - bP hits zero exactly at P = a/b.
    with pytest.raises(ValueError):
        compute(a=100.0, b=2.0, price=50.0)


def test_negative_price_raises():
    with pytest.raises(ValueError):
        compute(a=100.0, b=2.0, price=-1.0)


@pytest.mark.parametrize("a,b", [(-1.0, 2.0), (100.0, 0.0), (100.0, -2.0)])
def test_invalid_curve_params_raise(a, b):
    with pytest.raises(ValueError):
        compute(a, b, price=1.0)
