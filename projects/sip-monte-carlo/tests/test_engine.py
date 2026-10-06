import numpy as np
import pytest

from sip_monte_carlo.closed_form import future_value_growing_annuity
from sip_monte_carlo.engine import PERCENTILES, net_monthly_rate, run_simulation


# ---------------------------------------------------------------------------
# Required correctness property 1: zero volatility -> exact closed form
# ---------------------------------------------------------------------------


def test_zero_volatility_matches_closed_form_simple():
    result = run_simulation(
        monthly_contribution=15000.0,
        duration_years=10,
        expected_annual_return=0.12,
        annual_volatility=0.0,
        annual_inflation=0.0,
        contribution_growth_rate=0.0,
        initial_capital=0.0,
        annual_fee_rate=0.0,
        n_paths=5,
        seed=1,
    )
    r = net_monthly_rate(0.12, annual_fee_rate=0.0, annual_volatility=0.0)
    expected_fv = future_value_growing_annuity(15000.0, 10, r, 0.0, 0.0)
    # Every path is identical at zero volatility.
    assert np.allclose(result.nominal_final, expected_fv, rtol=1e-10)
    assert result.final_summary().loc["mean", "nominal"] == pytest.approx(expected_fv, rel=1e-10)


def test_zero_volatility_matches_closed_form_with_growth_fees_and_initial_capital():
    monthly_contribution = 20000.0
    years = 15
    expected_return = 0.11
    growth = 0.08
    fee = 0.015
    initial_capital = 200000.0

    result = run_simulation(
        monthly_contribution=monthly_contribution,
        duration_years=years,
        expected_annual_return=expected_return,
        annual_volatility=0.0,
        annual_inflation=0.06,
        contribution_growth_rate=growth,
        initial_capital=initial_capital,
        annual_fee_rate=fee,
        n_paths=3,
        seed=99,
    )
    r = net_monthly_rate(expected_return, annual_fee_rate=fee, annual_volatility=0.0)
    expected_fv = future_value_growing_annuity(
        monthly_contribution, years, r, growth, initial_capital
    )
    assert np.allclose(result.nominal_final, expected_fv, rtol=1e-9)


# ---------------------------------------------------------------------------
# Required correctness property 2: percentile monotonicity at every step
# ---------------------------------------------------------------------------


def test_percentiles_monotonic_at_every_time_step():
    result = run_simulation(
        monthly_contribution=10000.0,
        duration_years=20,
        expected_annual_return=0.12,
        annual_volatility=0.2,
        n_paths=3000,
        seed=7,
    )
    p = result.nominal_paths_percentiles
    stacked = np.vstack([p[q] for q in PERCENTILES])  # rows in order 10,25,50,75,90
    diffs = np.diff(stacked, axis=0)
    assert np.all(diffs >= -1e-6), "percentiles must be non-decreasing at every time step"

    p_real = result.real_paths_percentiles
    stacked_real = np.vstack([p_real[q] for q in PERCENTILES])
    diffs_real = np.diff(stacked_real, axis=0)
    assert np.all(diffs_real >= -1e-6)


# ---------------------------------------------------------------------------
# Required correctness property 3: same seed -> identical results
# ---------------------------------------------------------------------------


def test_same_seed_reproducible():
    kwargs = dict(
        monthly_contribution=15000.0,
        duration_years=10,
        expected_annual_return=0.12,
        annual_volatility=0.18,
        annual_inflation=0.05,
        contribution_growth_rate=0.05,
        initial_capital=50000.0,
        annual_fee_rate=0.01,
        n_paths=500,
        seed=12345,
    )
    r1 = run_simulation(**kwargs)
    r2 = run_simulation(**kwargs)
    assert np.array_equal(r1.nominal_final, r2.nominal_final)
    assert np.array_equal(r1.real_final, r2.real_final)
    for p in PERCENTILES:
        assert np.array_equal(
            r1.nominal_paths_percentiles[p], r2.nominal_paths_percentiles[p]
        )


def test_different_seed_gives_different_results():
    kwargs = dict(
        monthly_contribution=15000.0,
        duration_years=10,
        expected_annual_return=0.12,
        annual_volatility=0.18,
        n_paths=500,
    )
    r1 = run_simulation(seed=1, **kwargs)
    r2 = run_simulation(seed=2, **kwargs)
    assert not np.array_equal(r1.nominal_final, r2.nominal_final)


# ---------------------------------------------------------------------------
# Required correctness property 4: higher fees strictly reduce expected/median value
# ---------------------------------------------------------------------------


def test_higher_fees_strictly_reduce_expected_and_median_value():
    base_kwargs = dict(
        monthly_contribution=15000.0,
        duration_years=20,
        expected_annual_return=0.12,
        annual_volatility=0.18,
        annual_inflation=0.05,
        contribution_growth_rate=0.05,
        initial_capital=0.0,
        n_paths=4000,
        seed=42,
    )
    low_fee = run_simulation(annual_fee_rate=0.005, **base_kwargs)
    high_fee = run_simulation(annual_fee_rate=0.025, **base_kwargs)

    assert np.mean(high_fee.nominal_final) < np.mean(low_fee.nominal_final)
    assert np.median(high_fee.nominal_final) < np.median(low_fee.nominal_final)


# ---------------------------------------------------------------------------
# Required correctness property 5: higher volatility (fixed mean) does not
# increase the median -- variance drag / arithmetic-geometric mean gap.
# ---------------------------------------------------------------------------


def test_higher_volatility_does_not_increase_median_final_value():
    base_kwargs = dict(
        monthly_contribution=15000.0,
        duration_years=25,
        expected_annual_return=0.12,
        annual_inflation=0.0,
        contribution_growth_rate=0.0,
        initial_capital=0.0,
        annual_fee_rate=0.0,
        n_paths=6000,
        seed=2024,
    )
    low_vol = run_simulation(annual_volatility=0.05, **base_kwargs)
    high_vol = run_simulation(annual_volatility=0.30, **base_kwargs)

    # Same arithmetic mean assumption in both runs.
    assert low_vol.inputs["expected_annual_return"] == high_vol.inputs["expected_annual_return"]
    assert np.median(high_vol.nominal_final) < np.median(low_vol.nominal_final)


# ---------------------------------------------------------------------------
# Edge cases and invalid inputs
# ---------------------------------------------------------------------------


def test_zero_contribution_only_initial_capital_grows():
    result = run_simulation(
        monthly_contribution=0.0,
        duration_years=5,
        expected_annual_return=0.10,
        annual_volatility=0.0,
        initial_capital=100000.0,
        n_paths=2,
        seed=1,
    )
    r = net_monthly_rate(0.10, 0.0, 0.0)
    expected = 100000.0 * (1 + r) ** 60
    assert result.nominal_final[0] == pytest.approx(expected, rel=1e-9)


def test_one_year_duration_runs():
    result = run_simulation(
        monthly_contribution=5000.0,
        duration_years=1,
        n_paths=100,
        seed=3,
    )
    assert len(result.months) == 13
    assert result.nominal_final.shape == (100,)


def test_zero_fees_default_runs():
    result = run_simulation(
        monthly_contribution=5000.0,
        duration_years=3,
        annual_fee_rate=0.0,
        n_paths=50,
        seed=4,
    )
    assert np.all(result.nominal_final >= 0)


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(monthly_contribution=-1.0, duration_years=10),
        dict(monthly_contribution=1000.0, duration_years=0),
        dict(monthly_contribution=1000.0, duration_years=-5),
        dict(monthly_contribution=1000.0, duration_years=10, annual_volatility=-0.1),
        dict(monthly_contribution=1000.0, duration_years=10, n_paths=0),
        dict(monthly_contribution=1000.0, duration_years=10, n_paths=-10),
        dict(monthly_contribution=1000.0, duration_years=10, initial_capital=-5.0),
        dict(monthly_contribution=1000.0, duration_years=10, annual_fee_rate=-0.01),
        dict(monthly_contribution=1000.0, duration_years=10, annual_inflation=-1.5),
        dict(monthly_contribution=1000.0, duration_years=10, contribution_growth_rate=-2.0),
    ],
)
def test_invalid_inputs_raise_value_error(kwargs):
    with pytest.raises(ValueError):
        run_simulation(**kwargs)


def test_probability_of_reaching_target():
    result = run_simulation(
        monthly_contribution=15000.0,
        duration_years=20,
        expected_annual_return=0.12,
        annual_volatility=0.18,
        n_paths=3000,
        seed=5,
    )
    # A target of zero should always be reached.
    assert result.probability_of_reaching(0.0) == 1.0
    # An absurdly high target should almost never be reached.
    absurd_target = np.max(result.nominal_final) * 100
    assert result.probability_of_reaching(absurd_target) == 0.0
    # Monotonic in target.
    low = result.probability_of_reaching(1_000_000.0)
    high = result.probability_of_reaching(10_000_000.0)
    assert low >= high

    with pytest.raises(ValueError):
        result.probability_of_reaching(-1.0)


def test_final_summary_percentiles_ordered():
    result = run_simulation(
        monthly_contribution=15000.0,
        duration_years=15,
        annual_volatility=0.2,
        n_paths=2000,
        seed=6,
    )
    summary = result.final_summary()
    ordered_values = [summary.loc[f"p{p}", "nominal"] for p in PERCENTILES]
    assert ordered_values == sorted(ordered_values)
