"""Polymarket US (the CFTC-regulated US exchange) via its public gateway. No key needed for market data.

Separate from polymarket.com: different listings, USD settlement, and a per-market
fee coefficient Θ with fee = Θ × C × p × (1 − p).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Iterable, Iterator

from pmscan import http
from pmscan.models import Candidate
from pmscan.sources.common import Filters, Progress, normalize_category, num, parse_time

GATEWAY = "https://gateway.polymarket.us"
NAME = "polymarket_us"
PAGE = 500


def _quote(q) -> float | None:
    return num(q.get("value")) if isinstance(q, dict) else num(q)


def iter_events(f: Filters, progress: Progress | None = None) -> Iterator[dict]:
    offset = 0
    while True:
        data = http.get_json(f"{GATEWAY}/v1/events",
                             {"limit": PAGE, "offset": offset, "active": "true", "closed": "false"})
        events = data.get("events") or []
        if progress:
            progress(f"polymarket us: {offset + len(events)} events")
        yield from events
        if len(events) < PAGE:
            return
        offset += len(events)


def candidates_from_market(m: dict, event: dict, f: Filters) -> list[Candidate]:
    if m.get("closed") or not m.get("active", True) or m.get("hidden"):
        return []
    if (m.get("status") or "MARKET_STATUS_OPEN") != "MARKET_STATUS_OPEN":
        return []
    end = parse_time(m.get("endDate")) or parse_time(event.get("endDate"))
    if end is None or end <= f.now or (end - f.now).total_seconds() > f.max_days * 86400:
        return []

    bid, ask = _quote(m.get("bestBidQuote")), _quote(m.get("bestAskQuote"))
    yes_ask = ask
    no_ask = (1.0 - bid) if bid else None

    q = m.get("question") or ""
    t = m.get("title") or m.get("titleShort") or ""
    title = f"{q} — {t}" if t and q and t.lower() not in q.lower() else (q or t or event.get("title", ""))
    labels = [x.get("label") if isinstance(x, dict) else x for x in event.get("tags") or []]
    category = normalize_category([event.get("category"), m.get("category"), *labels], title)
    slug = event.get("slug") or ""

    out = []
    for side, price in (("Yes", yes_ask), ("No", no_ask)):
        if not f.in_band(price):
            continue
        out.append(Candidate(
            platform=NAME,
            market_id=m.get("slug") or str(m.get("id")),
            title=title,
            side=side,
            ask=round(price, 4),
            end_time=end,
            url=f"https://polymarket.us/event/{slug}" if slug else "https://polymarket.us",
            fee_rate=num(m.get("feeCoefficient")) or 0.0,
            book_ref=m.get("slug"),
            category=category,
            event=event.get("title") or "",
        ))
    return out


def scan(f: Filters, progress: Progress | None = None, events: Iterable[dict] | None = None) -> list[Candidate]:
    seen, out = set(), []
    for ev in events if events is not None else iter_events(f, progress):
        for m in ev.get("markets") or []:
            for c in candidates_from_market(m, ev, f):
                if (c.market_id, c.side) not in seen:
                    seen.add((c.market_id, c.side))
                    out.append(c)
    return out


def _asks_for(book: dict, side: str) -> list[tuple[float, float]]:
    """Book quotes the YES side. Buying YES lifts offers; buying NO hits YES bids at (1 − bid)."""
    lv = lambda rows: [(_quote(r.get("px")), num(r.get("qty")) or 0.0) for r in rows or []]
    if side == "Yes":
        return sorted((p, s) for p, s in lv(book.get("offers")) if p is not None)
    return sorted((round(1.0 - p, 4), s) for p, s in lv(book.get("bids")) if p is not None)


def fetch_book(c: Candidate) -> list[tuple[float, float]]:
    data = http.get_json(f"{GATEWAY}/v1/markets/{c.book_ref}/book")
    return _asks_for(data.get("marketData") or {}, c.side)


def fetch_books(cands: list[Candidate], progress: Progress | None = None) -> dict[str, list[tuple[float, float]]]:
    """No batch endpoint, so fetch per market in parallel. Also fills in volume/open interest from book stats.
    Returns {"slug|Side": ask levels}."""
    slugs = sorted({c.book_ref for c in cands if c.book_ref})
    raw: dict[str, dict] = {}

    def one(slug):
        try:
            return slug, (http.get_json(f"{GATEWAY}/v1/markets/{slug}/book").get("marketData") or {})
        except Exception:
            return slug, None

    with ThreadPoolExecutor(max_workers=8) as ex:
        for i, (slug, book) in enumerate(ex.map(one, slugs), 1):
            if book:
                raw[slug] = book
            if progress and i % 50 == 0:
                progress(f"polymarket us books: {i}/{len(slugs)}")

    out = {}
    for c in cands:
        book = raw.get(c.book_ref)
        if not book:
            continue
        stats = book.get("stats") or {}
        c.volume = _quote(stats.get("notionalTraded")) or 0.0
        c.liquidity = num(stats.get("openInterest")) or 0.0
        out[f"{c.book_ref}|{c.side}"] = _asks_for(book, c.side)
    return out
