import pytest

from econ_lab.modules.macro_multiplier import compute


def test_multiplier_matches_closed_form():
    result = compute(mpc=0.75, delta_g=100.0, rounds=5)
    assert result["multiplier"] == pytest.approx(1 / (1 - 0.75))
    assert result["multiplier"] == pytest.approx(4.0)
    assert result["delta_y"] == pytest.approx(400.0)


def test_round_spending_is_geometric_series():
    mpc, delta_g, rounds = 0.5, 100.0, 6
    result = compute(mpc=mpc, delta_g=delta_g, rounds=rounds)
    expected_rounds = [delta_g * (mpc ** i) for i in range(rounds)]
    assert result["round_spending"] == pytest.approx(expected_rounds)
    # Cumulative sum of a geometric series approaches delta_g/(1-mpc) as rounds -> infinity.
    assert result["cumulative"][-1] < result["delta_y"]
    assert result["cumulative"][-1] == pytest.approx(sum(expected_rounds))


def test_more_rounds_converges_closer_to_multiplier_limit():
    short = compute(mpc=0.8, delta_g=50.0, rounds=5)
    long = compute(mpc=0.8, delta_g=50.0, rounds=200)
    gap_short = abs(short["delta_y"] - short["cumulative"][-1])
    gap_long = abs(long["delta_y"] - long["cumulative"][-1])
    assert gap_long < gap_short
    assert long["cumulative"][-1] == pytest.approx(long["delta_y"], rel=1e-6)


def test_zero_mpc_gives_multiplier_of_one():
    result = compute(mpc=0.0, delta_g=75.0, rounds=3)
    assert result["multiplier"] == pytest.approx(1.0)
    assert result["delta_y"] == pytest.approx(75.0)


def test_negative_delta_g_is_a_contraction():
    result = compute(mpc=0.6, delta_g=-40.0, rounds=4)
    assert result["delta_y"] == pytest.approx(-40.0 / (1 - 0.6))
    assert result["delta_y"] < 0


@pytest.mark.parametrize("mpc", [1.0, 1.5, -0.1])
def test_invalid_mpc_raises(mpc):
    with pytest.raises(ValueError):
        compute(mpc=mpc, delta_g=10.0, rounds=3)


def test_invalid_rounds_raises():
    with pytest.raises(ValueError):
        compute(mpc=0.5, delta_g=10.0, rounds=0)
