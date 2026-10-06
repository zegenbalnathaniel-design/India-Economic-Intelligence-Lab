import pytest

from econ_lab.modules.micro_tax_incidence import compute


def test_hand_solved_tax_incidence_example():
    # Qd = 100 - 2*Pc, Qs = 10 + 1.5*Pp, tax t = 10.
    # No-tax: P0 = 90/3.5 = 25.714285714..., Q0 = 100-2*P0 = 48.571428571...
    # With tax: Pc = (90 + 1.5*10)/3.5 = 105/3.5 = 30 exactly.
    #           Pp = 30 - 10 = 20, Q = 100 - 2*30 = 40.
    result = compute(a=100.0, b=2.0, c=10.0, d=1.5, tax=10.0)

    assert result["p0"] == pytest.approx(90 / 3.5)
    assert result["q0"] == pytest.approx(100 - 2 * (90 / 3.5))
    assert result["p_consumer"] == pytest.approx(30.0)
    assert result["p_producer"] == pytest.approx(20.0)
    assert result["q_tax"] == pytest.approx(40.0)

    # Burden split: consumer = t*d/(b+d), producer = t*b/(b+d); must sum to t.
    assert result["consumer_burden"] == pytest.approx(10 * 1.5 / 3.5)
    assert result["producer_burden"] == pytest.approx(10 * 2.0 / 3.5)
    assert result["consumer_burden"] + result["producer_burden"] == pytest.approx(10.0)
    assert result["consumer_burden_share"] == pytest.approx(1.5 / 3.5)
    assert result["producer_burden_share"] == pytest.approx(2.0 / 3.5)

    # Triangle-area surplus and deadweight-loss formulas, hand-computed.
    demand_intercept_price = 100.0 / 2.0  # = 50
    supply_intercept_price = -10.0 / 1.5  # = -6.666...
    expected_cs = 0.5 * (demand_intercept_price - 30.0) * 40.0  # = 400
    expected_ps = 0.5 * (20.0 - supply_intercept_price) * 40.0  # = 533.33...
    expected_dwl = 0.5 * 10.0 * (result["q0"] - 40.0)
    assert result["consumer_surplus"] == pytest.approx(expected_cs)
    assert result["producer_surplus"] == pytest.approx(expected_ps)
    assert result["tax_revenue"] == pytest.approx(10.0 * 40.0)
    assert result["deadweight_loss"] == pytest.approx(expected_dwl)
    assert result["deadweight_loss"] == pytest.approx(42.857142857142854)


def test_zero_tax_matches_free_market_equilibrium():
    result = compute(a=100.0, b=2.0, c=10.0, d=1.5, tax=0.0)
    assert result["p_consumer"] == pytest.approx(result["p0"])
    assert result["p_producer"] == pytest.approx(result["p0"])
    assert result["q_tax"] == pytest.approx(result["q0"])
    assert result["deadweight_loss"] == pytest.approx(0.0)
    assert result["tax_revenue"] == pytest.approx(0.0)


def test_more_elastic_side_bears_less_burden():
    # Steeper supply slope relative to demand slope -> relatively less elastic
    # demand bears relatively more burden (consumer share = d/(b+d)).
    low_b = compute(a=100.0, b=1.0, c=10.0, d=5.0, tax=5.0)
    high_b = compute(a=100.0, b=5.0, c=10.0, d=5.0, tax=5.0)
    # Higher demand slope b => more elastic demand => consumers bear LESS.
    assert high_b["consumer_burden_share"] < low_b["consumer_burden_share"]


def test_negative_tax_raises():
    with pytest.raises(ValueError):
        compute(a=100.0, b=2.0, c=10.0, d=1.5, tax=-1.0)


def test_tax_too_large_raises():
    with pytest.raises(ValueError):
        compute(a=10.0, b=2.0, c=1.0, d=1.0, tax=1000.0)
