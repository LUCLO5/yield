"""Kalshi via the public Trade API v2 (market data endpoints need no key)."""

from __future__ import annotations

import time
from datetime import timedelta
from typing import Iterable, Iterator

from pmscan import fees, http
from pmscan.models import Candidate
from pmscan.sources.common import Filters, Progress, normalize_category, num, parse_time

API = "https://api.elections.kalshi.com/trade-api/v2"
NAME = "kalshi"
PAGE_DELAY = 0.15  # be polite; Kalshi rate-limits aggressively


def _dollars(m: dict, key: str) -> float | None:
    """Newer responses use `<key>_dollars` strings; older ones use integer cents."""
    v = num(m.get(f"{key}_dollars"))
    if v is not None:
        return v
    cents = num(m.get(key))
    return cents / 100.0 if cents is not None else None


def _fp(m: dict, key: str) -> float | None:
    v = num(m.get(f"{key}_fp"))
    return v if v is not None else num(m.get(key))


def iter_markets(f: Filters, progress: Progress | None = None) -> Iterator[dict]:
    cursor = ""
    pages = 0
    params = {
        "limit": 1000,
        "status": "open",
        "mve_filter": "exclude",  # skip auto-generated multi-leg parlays
        "min_close_ts": int(f.now.timestamp()),
        "max_close_ts": int((f.now + timedelta(days=f.max_days)).timestamp()),
    }
    while True:
        data = http.get_json(f"{API}/markets", {**params, "cursor": cursor})
        markets = data.get("markets") or []
        pages += 1
        if progress:
            progress(f"kalshi: page {pages}")
        yield from markets
        cursor = data.get("cursor") or ""
        if not cursor or not markets:
            return
        time.sleep(PAGE_DELAY)


def series_categories() -> dict[str, str]:
    """{SERIES_TICKER: Kalshi category}. One call returns every series."""
    try:
        data = http.get_json(f"{API}/series")
    except Exception:
        return {}
    return {s["ticker"].upper(): s.get("category") or "" for s in data.get("series") or [] if s.get("ticker")}


def candidates_from_market(m: dict, f: Filters, fee_rate: float = fees.KALSHI_TAKER_RATE,
                           categories: dict[str, str] | None = None) -> list[Candidate]:
    if (m.get("status") or "active") not in {"active", "open"}:
        return []
    end = parse_time(m.get("expected_expiration_time")) or parse_time(m.get("close_time"))
    if end is None or end <= f.now or (end - f.now).total_seconds() > f.max_days * 86400:
        return []
    volume = _fp(m, "volume") or 0.0
    if volume < f.min_volume:
        return []

    ticker = m.get("ticker", "")
    series = (m.get("event_ticker") or ticker).split("-")[0].lower()
    title = m.get("title") or ticker
    sub = m.get("yes_sub_title") or ""
    if sub and sub.lower() not in title.lower():
        title = f"{title} — {sub}"

    raw_cat = (categories or {}).get(series.upper(), "")
    category = normalize_category([raw_cat], title)
    out = []
    for side, ask_key, size_key in (("Yes", "yes_ask", "yes_ask_size"), ("No", "no_ask", "no_ask_size")):
        ask = _dollars(m, ask_key)
        if not f.in_band(ask):
            continue
        out.append(Candidate(
            platform=NAME,
            market_id=ticker,
            title=title,
            side=side,
            ask=round(ask, 4),
            end_time=end,
            url=f"https://kalshi.com/markets/{series}",
            volume=volume,
            liquidity=_fp(m, "open_interest") or 0.0,
            ask_size=_fp(m, size_key),
            fee_rate=fee_rate,
            fee_round_cent=True,
            book_ref=ticker,
            category=category,
            event=m.get("event_ticker") or "",
        ))
    return out


def scan(f: Filters, progress: Progress | None = None, markets: Iterable[dict] | None = None,
         fee_rate: float = fees.KALSHI_TAKER_RATE, categories: dict[str, str] | None = None) -> list[Candidate]:
    if categories is None:
        categories = series_categories() if markets is None else {}
    out: list[Candidate] = []
    for m in markets if markets is not None else iter_markets(f, progress):
        out.extend(candidates_from_market(m, f, fee_rate, categories))
    return out


def _asks_for(data: dict, side: str) -> list[tuple[float, float]]:
    """Kalshi books only list bids. Buying YES at p means hitting a NO bid at (1 - p), and vice versa."""
    if "orderbook_fp" in data:
        book = data["orderbook_fp"] or {}
        yes_bids = [(float(p), float(s)) for p, s in book.get("yes_dollars") or []]
        no_bids = [(float(p), float(s)) for p, s in book.get("no_dollars") or []]
    else:
        book = data.get("orderbook") or {}
        yes_bids = [(p / 100.0, float(s)) for p, s in book.get("yes") or []]
        no_bids = [(p / 100.0, float(s)) for p, s in book.get("no") or []]
    opposite = no_bids if side == "Yes" else yes_bids
    return sorted((round(1.0 - p, 4), s) for p, s in opposite)


def fetch_book(c: Candidate) -> list[tuple[float, float]]:
    return _asks_for(http.get_json(f"{API}/markets/{c.book_ref}/orderbook"), c.side)


def fetch_books(cands: list[Candidate], progress: Progress | None = None) -> dict[str, list[tuple[float, float]]]:
    """Batch: /markets/orderbooks takes up to 100 tickers. Returns {"TICKER|Side": ask levels}."""
    tickers = sorted({c.book_ref for c in cands if c.book_ref})
    raw: dict[str, dict] = {}
    for i in range(0, len(tickers), 100):
        chunk = tickers[i:i + 100]
        data = http.get_json(f"{API}/markets/orderbooks", [("tickers", t) for t in chunk])
        for b in data.get("orderbooks") or []:
            raw[b.get("ticker")] = b
        if progress:
            progress(f"kalshi books: {min(i + 100, len(tickers))}/{len(tickers)}")
        time.sleep(PAGE_DELAY)
    return {f"{c.book_ref}|{c.side}": _asks_for(raw[c.book_ref], c.side) for c in cands if c.book_ref in raw}
