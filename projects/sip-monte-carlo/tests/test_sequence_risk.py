import numpy as np
import pytest

from sip_monte_carlo.sequence_risk import (
    demo_sequence_of_returns_risk,
    simulate_annual_path,
)


def test_reversed_order_same_mean_different_final_value():
    annual_returns = [0.30, -0.10, 0.20, -0.05, 0.15]
    result = demo_sequence_of_returns_risk(
        annual_returns, annual_contribution=100000.0, initial_capital=0.0
    )
    assert result.arithmetic_mean_return == pytest.approx(np.mean(annual_returns))
    # Forward and reversed give the SAME mean return...
    assert np.mean(result.annual_returns_forward) == pytest.approx(
        np.mean(result.annual_returns_reversed)
    )
    # ...but DIFFERENT final wealth.
    assert result.forward_final != pytest.approx(result.reversed_final, rel=1e-9)
    assert result.difference == pytest.approx(result.forward_final - result.reversed_final)


def test_sequence_risk_vanishes_with_no_contributions():
    # With zero ongoing contributions, order of multiplication doesn't
    # matter (multiplication commutes), so forward and reversed must match.
    annual_returns = [0.30, -0.10, 0.20, -0.05, 0.15]
    result = demo_sequence_of_returns_risk(
        annual_returns, annual_contribution=0.0, initial_capital=100000.0
    )
    assert result.forward_final == pytest.approx(result.reversed_final, rel=1e-9)


def test_sequence_risk_zero_variance_returns_no_difference():
    annual_returns = [0.10, 0.10, 0.10, 0.10]
    result = demo_sequence_of_returns_risk(
        annual_returns, annual_contribution=50000.0, initial_capital=0.0
    )
    assert result.forward_final == pytest.approx(result.reversed_final, rel=1e-9)


def test_simulate_annual_path_matches_manual_computation():
    returns = [0.1, -0.2, 0.3]
    contribution = 1000.0
    fee = 0.01
    path = simulate_annual_path(returns, contribution, initial_capital=500.0, annual_fee_rate=fee)
    balance = 500.0
    expected = [balance]
    for r in returns:
        balance = balance * (1 + r - fee) + contribution
        expected.append(balance)
    assert np.allclose(path, expected)


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        simulate_annual_path([], 1000.0)
    with pytest.raises(ValueError):
        simulate_annual_path([0.1], -1000.0)
    with pytest.raises(ValueError):
        simulate_annual_path([0.1], 1000.0, initial_capital=-1.0)
    with pytest.raises(ValueError):
        simulate_annual_path([0.1], 1000.0, annual_fee_rate=-0.01)
