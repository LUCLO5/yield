"""Risk-free benchmark: US Treasury bill yields from FRED (no API key needed).

Each market is compared against the T-bill whose maturity is closest to the
market's time to resolution (1-month, 3-month, 6-month or 1-year).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pmscan import http

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"

# (label, FRED series, upper bound in days for using this tenor)
TENORS = [
    ("1M T-bill", "DGS1MO", 45),
    ("3M T-bill", "DGS3MO", 135),
    ("6M T-bill", "DGS6MO", 270),
    ("1Y T-bill", "DGS1", float("inf")),
]


@dataclass
class TBillCurve:
    rates: dict[str, float] = field(default_factory=dict)  # label -> annual rate as a decimal
    as_of: str = ""
    fixed: float | None = None  # user override (--rf)

    def rate_for(self, days: float) -> tuple[float, str]:
        if self.fixed is not None:
            return self.fixed, "fixed"
        for label, _, max_days in TENORS:
            if days <= max_days and label in self.rates:
                return self.rates[label], label
        label = next(iter(self.rates))
        return self.rates[label], label

    def describe(self) -> str:
        if self.fixed is not None:
            return f"fixed {self.fixed:.2%}"
        parts = ", ".join(f"{k.split()[0]} {v:.2%}" for k, v in self.rates.items())
        return f"T-bills {parts} (FRED, {self.as_of})"


def _latest(series: str) -> tuple[float, str]:
    text = http.get(FRED_CSV, {"id": series}).decode()
    for line in reversed(text.strip().splitlines()[1:]):
        date, _, value = line.partition(",")
        try:
            return float(value) / 100.0, date
        except ValueError:  # FRED uses "." for holidays
            continue
    raise ValueError(f"No data for {series}")


def load_curve(fixed: float | None = None) -> TBillCurve:
    if fixed is not None:
        return TBillCurve(fixed=fixed)
    curve = TBillCurve()
    for label, series, _ in TENORS:
        try:
            rate, date = _latest(series)
        except Exception:
            continue
        curve.rates[label] = rate
        curve.as_of = max(curve.as_of, date)
    if not curve.rates:
        raise RuntimeError("Couldn't fetch T-bill yields from FRED. Pass --rf 0.043 (for 4.3%) instead.")
    return curve
