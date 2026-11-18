from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional


@dataclass
class Candidate:
    """One side of one market that is priced at or above the probability threshold."""

    platform: str            # "polymarket" | "kalshi"
    market_id: str           # Polymarket conditionId / Kalshi ticker
    title: str               # human-readable question
    side: str                # outcome you would buy ("Yes", "No", "Team A", ...)
    ask: float               # best ask for that side, $ per share (0-1)
    end_time: datetime       # expected resolution / close (UTC)
    url: str
    volume: float = 0.0      # lifetime volume (USD on Polymarket, contracts on Kalshi)
    liquidity: float = 0.0   # Polymarket book liquidity / Kalshi open interest
    ask_size: Optional[float] = None   # shares available at the best ask, if known
    fee_rate: float = 0.0    # taker fee rate r in fee = r * C * p * (1 - p)
    fee_round_cent: bool = False       # Kalshi rounds fees up to the next cent
    book_ref: Optional[str] = None     # token id / ticker used to fetch the order book
    category: str = "Other"
    event: str = ""                    # parent event title (for grouping / search)
    flags: list[str] = field(default_factory=list)


@dataclass
class Fill:
    shares: float
    cost: float      # dollars paid for shares, excluding fees
    fees: float
    levels: int      # how many price levels were consumed
    complete: bool   # False if the book ran out before the stake was spent
    from_book: bool = False  # True if priced off the live order book, not just the quote

    @property
    def spent(self) -> float:
        return self.cost + self.fees

    @property
    def avg_price(self) -> float:
        return self.cost / self.shares if self.shares else 0.0


@dataclass
class Result:
    cand: Candidate
    stake: float
    fill: Fill
    days: float
    payout: float
    profit: float
    roi: float                 # profit / spent, over the holding period
    simple_annual: float       # roi * 365 / days
    apy: float                 # (1 + roi) ** (365 / days) - 1
    tbill_rate: float          # annual T-bill yield used for comparison
    tbill_tenor: str
    tbill_profit: float        # what `spent` would earn in T-bills over the same days
    excess_vs_tbill: float     # profit - tbill_profit
    breakeven_prob: float      # true win probability needed to not lose money
    breakeven_prob_vs_tbill: float  # ... needed to match T-bills
    wins_to_cover_loss: float  # how many winning trades one loss wipes out


BookFetcher = Callable[[Candidate], list[tuple[float, float]]]
