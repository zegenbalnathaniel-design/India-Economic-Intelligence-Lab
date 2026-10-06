import math

import pytest

from econ_lab.modules.finance_diversification import compute


def test_perfect_positive_correlation_gives_no_diversification_benefit():
    # rho=1 -> portfolio std = weighted average of the two stds exactly.
    result = compute(w1=0.5, sigma1=20.0, sigma2=30.0, rho=1.0)
    expected_std = 0.5 * 20.0 + 0.5 * 30.0
    assert result["portfolio_std"] == pytest.approx(expected_std)
    assert result["undiversified_std"] == pytest.approx(expected_std)
    assert result["diversification_benefit"] == pytest.approx(0.0, abs=1e-9)


def test_perfect_negative_correlation_hand_solved():
    # rho=-1 -> variance = (w1*s1 - w2*s2)^2 exactly.
    result = compute(w1=0.5, sigma1=20.0, sigma2=30.0, rho=-1.0)
    expected_variance = (0.5 * 20.0 - 0.5 * 30.0) ** 2
    assert result["portfolio_variance"] == pytest.approx(expected_variance)
    assert result["portfolio_variance"] == pytest.approx(25.0)
    assert result["portfolio_std"] == pytest.approx(5.0)
    assert result["undiversified_std"] == pytest.approx(25.0)
    assert result["diversification_benefit"] == pytest.approx(20.0)


def test_zero_correlation_matches_exact_formula():
    w1, s1, s2, rho = 0.5, 20.0, 30.0, 0.0
    result = compute(w1=w1, sigma1=s1, sigma2=s2, rho=rho)
    w2 = 1 - w1
    expected_variance = (w1 ** 2) * (s1 ** 2) + (w2 ** 2) * (s2 ** 2)
    assert result["portfolio_variance"] == pytest.approx(expected_variance)
    assert result["portfolio_std"] == pytest.approx(math.sqrt(expected_variance))


def test_benefit_decreases_monotonically_as_correlation_rises():
    low_rho = compute(w1=0.4, sigma1=15.0, sigma2=25.0, rho=-0.8)
    mid_rho = compute(w1=0.4, sigma1=15.0, sigma2=25.0, rho=0.0)
    high_rho = compute(w1=0.4, sigma1=15.0, sigma2=25.0, rho=0.8)
    assert low_rho["portfolio_std"] < mid_rho["portfolio_std"] < high_rho["portfolio_std"]
    assert low_rho["diversification_benefit"] > mid_rho["diversification_benefit"] > high_rho["diversification_benefit"]


def test_zero_volatility_assets_have_zero_risk():
    result = compute(w1=0.5, sigma1=0.0, sigma2=0.0, rho=0.3)
    assert result["portfolio_variance"] == pytest.approx(0.0)
    assert result["portfolio_std"] == pytest.approx(0.0)


@pytest.mark.parametrize("w1,sigma1,sigma2,rho", [
    (-0.1, 20.0, 30.0, 0.0),
    (1.1, 20.0, 30.0, 0.0),
    (0.5, -5.0, 30.0, 0.0),
    (0.5, 20.0, -5.0, 0.0),
    (0.5, 20.0, 30.0, 1.5),
    (0.5, 20.0, 30.0, -1.5),
])
def test_invalid_inputs_raise(w1, sigma1, sigma2, rho):
    with pytest.raises(ValueError):
        compute(w1=w1, sigma1=sigma1, sigma2=sigma2, rho=rho)
