import pytest

from econ_lab.modules.macro_growth import compute


def test_steady_state_matches_closed_form():
    # alpha=0.5 gives a clean closed form: k* = (s/delta)^2, y* = s/delta.
    s, delta, alpha = 0.25, 0.08, 0.5
    result = compute(s=s, delta=delta, alpha=alpha, k0=1.0, periods=5)
    expected_k_star = (s / delta) ** (1.0 / (1.0 - alpha))
    assert result["k_star"] == pytest.approx(expected_k_star)
    assert result["k_star"] == pytest.approx((s / delta) ** 2)
    assert result["k_star"] == pytest.approx(9.765625)
    assert result["y_star"] == pytest.approx(s / delta)
    assert result["y_star"] == pytest.approx(3.125)


def test_path_converges_to_steady_state_regardless_of_start():
    s, delta, alpha = 0.3, 0.1, 0.33
    low_start = compute(s=s, delta=delta, alpha=alpha, k0=0.2, periods=500)
    high_start = compute(s=s, delta=delta, alpha=alpha, k0=20.0, periods=500)
    k_star = low_start["k_star"]
    assert low_start["capital_path"][-1] == pytest.approx(k_star, rel=1e-3)
    assert high_start["capital_path"][-1] == pytest.approx(k_star, rel=1e-3)


def test_higher_savings_rate_raises_steady_state():
    low_s = compute(s=0.1, delta=0.08, alpha=0.4, k0=1.0, periods=10)
    high_s = compute(s=0.4, delta=0.08, alpha=0.4, k0=1.0, periods=10)
    assert high_s["k_star"] > low_s["k_star"]
    assert high_s["y_star"] > low_s["y_star"]


def test_zero_starting_capital_stays_at_zero():
    result = compute(s=0.25, delta=0.08, alpha=0.5, k0=0.0, periods=20)
    assert all(k == pytest.approx(0.0) for k in result["capital_path"])
    assert all(y == pytest.approx(0.0) for y in result["output_path"])


@pytest.mark.parametrize("s,delta,alpha,k0,periods", [
    (0.0, 0.08, 0.5, 1.0, 10),     # s not in (0,1)
    (1.0, 0.08, 0.5, 1.0, 10),
    (0.25, 0.0, 0.5, 1.0, 10),     # delta not in (0,1)
    (0.25, 1.0, 0.5, 1.0, 10),
    (0.25, 0.08, 0.0, 1.0, 10),    # alpha not in (0,1)
    (0.25, 0.08, 1.0, 1.0, 10),
    (0.25, 0.08, 0.5, -1.0, 10),   # negative k0
    (0.25, 0.08, 0.5, 1.0, 0),     # periods < 1
])
def test_invalid_inputs_raise(s, delta, alpha, k0, periods):
    with pytest.raises(ValueError):
        compute(s=s, delta=delta, alpha=alpha, k0=k0, periods=periods)
