from datetime import datetime, timedelta, timezone

import pytest

from pmscan import calc, fees
from pmscan.benchmark import TBillCurve
from pmscan.models import Candidate

NOW = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
CURVE = TBillCurve(rates={"1M T-bill": 0.04, "3M T-bill": 0.043, "6M T-bill": 0.044, "1Y T-bill": 0.045}, as_of="x")


def cand(ask=0.96, days=10, platform="polymarket", fee_rate=0.0, round_cent=False, size=None):
    return Candidate(platform=platform, market_id="m", title="t", side="Yes", ask=ask,
                     end_time=NOW + timedelta(days=days), url="u", fee_rate=fee_rate,
                     fee_round_cent=round_cent, ask_size=size)


def test_kalshi_fee_matches_published_example():
    # Kalshi's schedule: 100 contracts at $0.50 -> $1.75
    assert fees.fee(100, 0.50, 0.07, round_up_cent=True) == 1.75
    # rounds up to the next cent
    assert fees.fee(1, 0.96, 0.07, round_up_cent=True) == 0.01


def test_polymarket_fee_formula():
    # C * rate * p * (1 - p)
    assert fees.fee(100, 0.5, 0.04) == pytest.approx(1.0)
    assert fees.fee(100, 0.96, 0.0) == 0.0


def test_no_fee_yield_math():
    c = cand(ask=0.96, days=10)
    r = calc.evaluate(c, 1000, calc.top_of_book_fill(c, 1000), NOW, CURVE)
    assert r.fill.shares == pytest.approx(1000 / 0.96)
    assert r.profit == pytest.approx(1000 / 0.96 - 1000)
    assert r.roi == pytest.approx(0.04 / 0.96)
    assert r.simple_annual == pytest.approx(r.roi * 36.5)
    assert r.apy == pytest.approx((1 + r.roi) ** 36.5 - 1)
    assert r.tbill_tenor == "1M T-bill"
    assert r.tbill_profit == pytest.approx(1000 * 0.04 * 10 / 365)
    assert r.breakeven_prob == pytest.approx(0.96)
    assert r.wins_to_cover_loss == pytest.approx(1000 / r.profit)


def test_kalshi_whole_contracts_and_fee():
    c = cand(ask=0.96, days=4, platform="kalshi", fee_rate=0.07, round_cent=True)
    f = calc.top_of_book_fill(c, 1000)
    assert f.shares == 1038
    assert f.fees == 2.80
    assert f.spent <= 1000
    r = calc.evaluate(c, 1000, f, NOW, CURVE)
    assert r.profit == pytest.approx(38.72, abs=0.01)


def test_book_walk_uses_worse_prices_and_flags_thin_book():
    levels = [(0.97, 500), (0.96, 100), (0.98, 10_000)]  # unsorted on purpose
    f = calc.simulate_fill(levels, 1000, 0.0)
    assert f.levels == 3
    assert 0.96 < f.avg_price < 0.98
    assert f.complete

    thin = calc.simulate_fill([(0.97, 10)], 1000, 0.0)
    assert not thin.complete
    assert thin.shares == 10


def test_tenor_selection_and_override():
    assert CURVE.rate_for(100)[1] == "3M T-bill"
    assert CURVE.rate_for(200)[1] == "6M T-bill"
    assert CURVE.rate_for(400)[1] == "1Y T-bill"
    assert TBillCurve(fixed=0.05).rate_for(10) == (0.05, "fixed")
