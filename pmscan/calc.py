"""Fill simulation and yield math."""

from __future__ import annotations

import math
from datetime import datetime

from pmscan import fees
from pmscan.benchmark import TBillCurve
from pmscan.models import Candidate, Fill, Result


def simulate_fill(levels: list[tuple[float, float]], stake: float, fee_rate: float, *,
                  round_up_cent: bool = False, whole_shares: bool = False) -> Fill:
    """Spend `stake` dollars (fees included) walking up the ask side of a book.

    `levels` is [(price, size), ...]; it is sorted cheapest-first here.
    """
    remaining = stake
    shares = cost = fee_raw = 0.0
    used = 0
    for price, size in sorted(levels):
        if remaining <= 0 or price <= 0 or price >= 1:
            break
        all_in = price + fees.per_share(price, fee_rate)
        take = min(size, remaining / all_in)
        if whole_shares:
            take = math.floor(take + 1e-9)
        if take <= 0:
            break
        used += 1
        shares += take
        cost += take * price
        fee_raw += take * fees.per_share(price, fee_rate)
        remaining -= take * all_in
        if take < size:
            break

    fee_paid = math.ceil(fee_raw * 100 - 1e-9) / 100 if (round_up_cent and fee_raw > 0) else fee_raw
    # Rounding the fee up can push total spend a hair over the stake; drop shares to fit.
    if round_up_cent and cost + fee_paid > stake + 1e-9 and shares > 0:
        avg = cost / shares
        while shares > 0 and cost + fee_paid > stake + 1e-9:
            shares -= 1 if whole_shares else 0.01
            cost = shares * avg
            fee_paid = fees.fee(shares, avg, fee_rate, round_up_cent=True)

    complete = (stake - (cost + fee_paid)) < max(1.0, 0.01 * stake)
    return Fill(shares=max(shares, 0.0), cost=cost, fees=fee_paid, levels=used, complete=complete)


def top_of_book_fill(c: Candidate, stake: float) -> Fill:
    size = c.ask_size if c.ask_size and c.ask_size > 0 else float("inf")
    return simulate_fill([(c.ask, size)], stake, c.fee_rate,
                         round_up_cent=c.fee_round_cent, whole_shares=c.platform == "kalshi")


def evaluate(c: Candidate, stake: float, fill: Fill, now: datetime, curve: TBillCurve) -> Result | None:
    if fill.shares <= 0:
        return None
    days = max((c.end_time - now).total_seconds() / 86400.0, 1e-6)
    spent = fill.spent
    payout = fill.shares * 1.0
    profit = payout - spent
    roi = profit / spent
    simple = roi * 365.0 / days
    try:
        apy = (1.0 + roi) ** (365.0 / days) - 1.0
    except OverflowError:
        apy = math.inf

    rate, tenor = curve.rate_for(days)
    tbill_profit = spent * rate * days / 365.0
    return Result(
        cand=c, stake=stake, fill=fill, days=days, payout=payout, profit=profit, roi=roi,
        simple_annual=simple, apy=apy, tbill_rate=rate, tbill_tenor=tenor,
        tbill_profit=tbill_profit, excess_vs_tbill=profit - tbill_profit,
        breakeven_prob=spent / payout,
        breakeven_prob_vs_tbill=(spent + tbill_profit) / payout,
        wins_to_cover_loss=(spent / profit) if profit > 0 else math.inf,
    )
