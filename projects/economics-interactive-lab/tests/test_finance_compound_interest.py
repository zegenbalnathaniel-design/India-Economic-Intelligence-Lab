import pytest

from econ_lab.modules.finance_compound_interest import compute


def test_lump_sum_matches_standard_formula():
    principal, rate, periods = 10000.0, 0.07, 20
    result = compute(principal=principal, rate=rate, periods=periods, contribution=0.0)
    expected_fv = principal * (1 + rate) ** periods
    assert result["fv_lump"] == pytest.approx(expected_fv)
    assert result["fv_total"] == pytest.approx(expected_fv)


def test_annuity_matches_standard_formula():
    contribution, rate, periods = 1000.0, 0.07, 20
    result = compute(principal=0.0, rate=rate, periods=periods, contribution=contribution)
    expected_fv_annuity = contribution * (((1 + rate) ** periods - 1) / rate)
    assert result["fv_annuity"] == pytest.approx(expected_fv_annuity)


def test_combined_lump_sum_and_annuity():
    principal, contribution, rate, periods = 10000.0, 1000.0, 0.07, 20
    result = compute(principal=principal, rate=rate, periods=periods, contribution=contribution)
    expected_lump = principal * (1 + rate) ** periods
    expected_annuity = contribution * (((1 + rate) ** periods - 1) / rate)
    assert result["fv_lump"] == pytest.approx(expected_lump)
    assert result["fv_annuity"] == pytest.approx(expected_annuity)
    assert result["fv_total"] == pytest.approx(expected_lump + expected_annuity)


def test_present_value_discounts_future_value_back_exactly():
    result = compute(principal=10000.0, rate=0.07, periods=20, contribution=1000.0)
    recovered_fv = result["present_value"] * (1 + 0.07) ** 20
    assert recovered_fv == pytest.approx(result["fv_total"])


def test_zero_rate_is_simple_linear_accumulation():
    # With r=0, FV_lump = principal exactly; FV_annuity = contribution * periods exactly.
    result = compute(principal=5000.0, rate=0.0, periods=10, contribution=200.0)
    assert result["fv_lump"] == pytest.approx(5000.0)
    assert result["fv_annuity"] == pytest.approx(2000.0)
    assert result["fv_total"] == pytest.approx(7000.0)
    assert result["present_value"] == pytest.approx(7000.0)


def test_zero_periods_returns_principal_only():
    result = compute(principal=1234.0, rate=0.05, periods=0, contribution=500.0)
    assert result["fv_lump"] == pytest.approx(1234.0)
    assert result["fv_annuity"] == pytest.approx(0.0)
    assert result["balance_path"] == [1234.0]


@pytest.mark.parametrize("principal,rate,periods,contribution", [
    (-100.0, 0.05, 10, 0.0),
    (100.0, -1.5, 10, 0.0),
    (100.0, 0.05, -1, 0.0),
    (100.0, 0.05, 10, -50.0),
])
def test_invalid_inputs_raise(principal, rate, periods, contribution):
    with pytest.raises(ValueError):
        compute(principal=principal, rate=rate, periods=periods, contribution=contribution)
