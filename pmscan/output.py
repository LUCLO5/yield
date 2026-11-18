from __future__ import annotations

import csv
import json
import math
import shutil
from typing import Sequence

from pmscan.models import Result


def _pct(x: float, digits: int = 1) -> str:
    if math.isinf(x):
        return "inf"
    return f"{x * 100:,.{digits}f}%"


def _days(d: float) -> str:
    if d < 1 / 24:
        return "<1h"
    return f"{d * 24:.0f}h" if d < 1 else f"{d:.1f}"


def _trunc(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def table(results: Sequence[Result], stake: float) -> str:
    width = shutil.get_terminal_size((160, 40)).columns
    headers = ["#", "Venue", "Market", "Buy", "Price", "Days", f"Profit/${stake:,.0f}",
               "ROI", "Annual", "T-bill", "Excess $", "1 loss =", "Src", "Flags"]
    rows = []
    for i, r in enumerate(results, 1):
        c = r.cand
        rows.append([
            str(i),
            {"polymarket": "PM", "polymarket_us": "PU"}.get(c.platform, "KX"),
            c.title,
            _trunc(c.side, 14),
            f"{r.fill.avg_price:.3f}",
            _days(r.days),
            f"${r.profit:,.2f}",
            _pct(r.roi, 2),
            _pct(r.simple_annual),
            _pct(r.tbill_rate, 2),
            f"{r.excess_vs_tbill:+,.2f}",
            "∞" if math.isinf(r.wins_to_cover_loss) else f"{r.wins_to_cover_loss:,.0f} wins",
            "book" if r.fill.from_book else "quote",
            ", ".join(c.flags + ([] if r.fill.complete else ["thin book"])),
        ])
    # size the Market column to whatever space is left
    fixed = sum(max(len(h), *(len(row[j]) for row in rows)) + 2
                for j, h in enumerate(headers) if j != 2) if rows else 0
    title_w = max(24, min(70, width - fixed - 2))
    for row in rows:
        row[2] = _trunc(row[2], title_w)
    widths = [max(len(h), *(len(row[j]) for row in rows)) if rows else len(h) for j, h in enumerate(headers)]
    right = {0, 4, 5, 6, 7, 8, 9, 10, 11}

    def fmt(cells):
        return "  ".join(c.rjust(w) if j in right else c.ljust(w) for j, (c, w) in enumerate(zip(cells, widths)))

    lines = [fmt(headers), fmt(["-" * w for w in widths])]
    lines += [fmt(r) for r in rows]
    return "\n".join(lines)


def to_records(results: Sequence[Result]) -> list[dict]:
    out = []
    for r in results:
        c = r.cand
        out.append({
            "platform": c.platform,
            "market_id": c.market_id,
            "title": c.title,
            "side": c.side,
            "quoted_ask": c.ask,
            "avg_fill_price": round(r.fill.avg_price, 5),
            "shares": round(r.fill.shares, 4),
            "stake": r.stake,
            "spent": round(r.fill.spent, 4),
            "fees": round(r.fill.fees, 4),
            "payout_if_win": round(r.payout, 4),
            "profit_if_win": round(r.profit, 4),
            "roi": round(r.roi, 6),
            "annualized_simple": round(r.simple_annual, 6),
            "apy_compounded": None if math.isinf(r.apy) else round(r.apy, 6),
            "end_time": c.end_time.isoformat(),
            "days_to_resolution": round(r.days, 4),
            "tbill_tenor": r.tbill_tenor,
            "tbill_rate": r.tbill_rate,
            "tbill_profit_same_period": round(r.tbill_profit, 4),
            "excess_vs_tbill": round(r.excess_vs_tbill, 4),
            "breakeven_win_prob": round(r.breakeven_prob, 6),
            "breakeven_win_prob_vs_tbill": round(r.breakeven_prob_vs_tbill, 6),
            "wins_to_cover_one_loss": None if math.isinf(r.wins_to_cover_loss) else round(r.wins_to_cover_loss, 2),
            "volume": c.volume,
            "liquidity": c.liquidity,
            "priced_from": "order_book" if r.fill.from_book else "top_quote",
            "fill_complete": r.fill.complete,
            "book_levels_used": r.fill.levels,
            "flags": "; ".join(c.flags),
            "url": c.url,
        })
    return out


def write_csv(results: Sequence[Result], path: str) -> None:
    recs = to_records(results)
    if not recs:
        open(path, "w").close()
        return
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(recs[0]))
        w.writeheader()
        w.writerows(recs)


def write_json(results: Sequence[Result], path: str) -> None:
    with open(path, "w") as fh:
        json.dump(to_records(results), fh, indent=2)
