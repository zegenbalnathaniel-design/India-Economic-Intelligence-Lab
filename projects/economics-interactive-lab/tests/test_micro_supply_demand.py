import pytest

from econ_lab.modules.micro_supply_demand import compute


def test_equilibrium_matches_hand_solved_algebra():
    # Qd = 100 - 2P, Qs = 10 + 1.5P
    # 100 - 2P = 10 + 1.5P  =>  90 = 3.5P  =>  P* = 90/3.5
    a, b, c, d = 100.0, 2.0, 10.0, 1.5
    result = compute(a, b, c, d)
    expected_p = (a - c) / (b + d)
    expected_q = a - b * expected_p
    assert result["p_star"] == pytest.approx(expected_p)
    assert result["q_star"] == pytest.approx(expected_q)
    # Cross-check with the hand-solved fraction directly.
    assert result["p_star"] == pytest.approx(90 / 3.5)
    assert result["q_star"] == pytest.approx(100 - 2 * (90 / 3.5))


def test_equilibrium_satisfies_both_curves():
    a, b, c, d = 50.0, 1.0, 5.0, 0.5
    result = compute(a, b, c, d)
    qd = a - b * result["p_star"]
    qs = c + d * result["p_star"]
    assert qd == pytest.approx(qs)
    assert qd == pytest.approx(result["q_star"])


def test_simple_symmetric_case():
    # Qd = 20 - P, Qs = 0 + P -> 20-P = P -> P*=10, Q*=10
    result = compute(a=20.0, b=1.0, c=0.0, d=1.0)
    assert result["p_star"] == pytest.approx(10.0)
    assert result["q_star"] == pytest.approx(10.0)


@pytest.mark.parametrize("a,b,c,d", [
    (100.0, -1.0, 10.0, 1.0),   # negative demand slope
    (100.0, 1.0, 10.0, -1.0),   # negative supply slope
    (-5.0, 1.0, 10.0, 1.0),     # negative demand intercept
    (100.0, 1.0, -10.0, 1.0),   # negative supply intercept
])
def test_invalid_inputs_raise(a, b, c, d):
    with pytest.raises(ValueError):
        compute(a, b, c, d)


def test_no_positive_price_equilibrium_raises():
    # Supply intercept exceeds demand intercept -> no positive-price crossing.
    with pytest.raises(ValueError):
        compute(a=5.0, b=1.0, c=10.0, d=1.0)
