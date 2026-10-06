import pytest

from econ_lab.modules.macro_ad_as import compute


def test_baseline_equilibrium_matches_hand_solved_algebra():
    # AD: Y=300-3P, AS: Y=50+2P -> 300-3P=50+2P -> 250=5P -> P=50, Y=300-150=150
    result = compute(ad_intercept=300.0, ad_slope=3.0, as_intercept=50.0, as_slope=2.0)
    assert result["p0"] == pytest.approx(50.0)
    assert result["y0"] == pytest.approx(150.0)
    # No shock given -> shocked equilibrium equals baseline.
    assert result["p1"] == pytest.approx(50.0)
    assert result["y1"] == pytest.approx(150.0)
    assert result["delta_y"] == pytest.approx(0.0)
    assert result["delta_p"] == pytest.approx(0.0)


def test_demand_shock_raises_both_price_and_output():
    # AD intercept shifted to 330: (330-50)/5=56 -> Y=330-168=162
    result = compute(ad_intercept=300.0, ad_slope=3.0, as_intercept=50.0, as_slope=2.0, ad_shift=30.0)
    assert result["p1"] == pytest.approx(56.0)
    assert result["y1"] == pytest.approx(162.0)
    assert result["delta_y"] > 0
    assert result["delta_p"] > 0


def test_combined_demand_and_supply_shock_hand_solved():
    # ad_intercept -> 330, as_intercept -> 40: P1=(330-40)/5=58, Y1=330-174=156
    result = compute(
        ad_intercept=300.0, ad_slope=3.0, as_intercept=50.0, as_slope=2.0,
        ad_shift=30.0, as_shift=-10.0,
    )
    assert result["p1"] == pytest.approx(58.0)
    assert result["y1"] == pytest.approx(156.0)
    assert result["delta_y"] == pytest.approx(6.0)
    assert result["delta_p"] == pytest.approx(8.0)


def test_negative_supply_shock_raises_price_lowers_output():
    # Pure negative supply shock: as_intercept -> 30: P1=(300-30)/5=54, Y1=300-162=138
    result = compute(ad_intercept=300.0, ad_slope=3.0, as_intercept=50.0, as_slope=2.0, as_shift=-20.0)
    assert result["delta_p"] > 0
    assert result["delta_y"] < 0


@pytest.mark.parametrize("ad_slope,as_slope", [(0.0, 2.0), (3.0, 0.0), (-1.0, 2.0)])
def test_invalid_slopes_raise(ad_slope, as_slope):
    with pytest.raises(ValueError):
        compute(ad_intercept=300.0, ad_slope=ad_slope, as_intercept=50.0, as_slope=as_slope)
