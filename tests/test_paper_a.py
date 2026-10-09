"""Paper A (author's income & wealth inequality paper): Table 1 returns and
Figure 2, as used in the Wealth Lab's sections D and E."""
from __future__ import annotations

import numpy as np
import pytest

from analysis import wealth as W
from data_sources import loaders as L


@pytest.fixture(scope="module")
def returns():
    r = L.load_paper_a_returns().set_index("asset")["nominal_return_1991_2021_pct"] / 100
    return r


def test_table1_values_transcribed(returns):
    assert returns["Residential property"] == pytest.approx(0.093)
    assert returns["Gold"] == pytest.approx(0.092)
    assert returns["Financial assets: listed equity"] == pytest.approx(0.135)
    shares = L.load_paper_a_returns().set_index("asset")["share_of_household_assets_pct"]
    assert shares[["Residential property", "Gold", "Durable goods", "Financial assets: deposits"]].sum() == 100


def test_figure2_endpoints_reproduced():
    for r in L.load_paper_a_figure2().itertuples():
        fv = W.annuity_path(r.annual_contribution_inr, r.nominal_return_pct / 100, r.years)[-1] / 1e7
        assert fv == pytest.approx(r.final_value_crore_stated, abs=0.011)  # printed to 2 dp


def test_annuity_path_shape_and_zero_rate():
    p = W.annuity_path(100000, 0.1, 3)
    assert p[0] == 0 and p[1] == pytest.approx(100000) and p[3] == pytest.approx(100000 * (1.1**3 - 1) / 0.1)
    assert W.annuity_path(100000, 0.0, 30)[-1] == pytest.approx(3_000_000)


def test_table1_real_return_columns_at_6_5_pct(returns):
    rmg = W.real_minus_g({"property": returns["Residential property"], "gold": returns["Gold"],
                          "equity": returns["Financial assets: listed equity"],
                          "deposits": returns["Financial assets: deposits"]}, 0.065, 0.065).set_index("asset")
    assert 0.02 <= rmg.loc["property", "real"] <= 0.03            # Table 1: 2~3%
    assert 0.02 <= rmg.loc["gold", "real"] <= 0.04                # 2~4%
    assert 0.06 <= rmg.loc["equity", "real"] <= 0.07              # 6~7%
    assert abs(rmg.loc["deposits", "real"]) < 0.005               # ~0%
    assert -0.05 <= rmg.loc["property", "r_minus_g"] <= -0.03     # -3 to -5 pts
    assert -0.01 <= rmg.loc["equity", "r_minus_g"] <= 0.01        # -1 to +1 pts


def test_allocation_ranking_orders_by_return():
    rank = W.allocation_ranking({"a": 0.135, "b": 0.092, "c": 0.065}, 100000, 30, 0.065)
    assert rank["allocation"].tolist() == ["a", "b", "c"]
    assert rank["multiple_of_last"].iloc[-1] == 1
    assert rank["final_real"].iloc[0] == pytest.approx(rank["final_nominal"].iloc[0] / 1.065**30)


def test_equity_mix_and_excess_growth():
    assert W.equity_mix_return(0.5, 0.135, 0.092) == pytest.approx(0.1135)
    with pytest.raises(ValueError):
        W.equity_mix_return(1.2, 0.1, 0.1)
    assert W.implied_excess_growth(3.83, 5.75, 27) == pytest.approx((5.75 / 3.83) ** (1 / 27) - 1)
    assert np.isclose(W.implied_excess_growth(2, 2, 10), 0)
