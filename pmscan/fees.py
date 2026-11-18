"""Taker-fee formulas.

Polymarket: fee = C * feeRate * p * (1 - p)        (per-market feeRate; 0 when fees are off)
            https://docs.polymarket.com/trading/fees
Kalshi:     fee = round_up(M * 0.07 * C * P * (1 - P)) to the next cent (general schedule)
            https://kalshi.com/fee-schedule

Both shrink toward zero near $0.99, which is why 96%+ markets are cheap to trade.
"""

from __future__ import annotations

import math

KALSHI_TAKER_RATE = 0.07


def fee(shares: float, price: float, rate: float, *, round_up_cent: bool = False) -> float:
    if shares <= 0 or rate <= 0:
        return 0.0
    raw = rate * shares * price * (1.0 - price)
    if round_up_cent:
        # tiny epsilon so 1.75 doesn't become 1.76 through float noise
        return math.ceil(raw * 100 - 1e-9) / 100
    return raw


def per_share(price: float, rate: float) -> float:
    return rate * price * (1.0 - price)
