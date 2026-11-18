"""Polymarket via the public Gamma API (market list) and CLOB API (order books). No key needed."""

from __future__ import annotations

from datetime import timedelta
from typing import Iterable, Iterator

from pmscan import http
from pmscan.models import Candidate
from pmscan.sources.common import Filters, Progress, json_list, normalize_category, num, parse_time

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
NAME = "polymarket"


def iter_events(f: Filters, progress: Progress | None = None) -> Iterator[dict]:
    cursor = None
    pages = 0
    params = {
        "limit": 500,
        "closed": "false",
        "end_date_min": f.now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end_date_max": (f.now + timedelta(days=f.max_days)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    while True:
        data = http.get_json(f"{GAMMA}/events/keyset", {**params, "after_cursor": cursor})
        events = data.get("events") or []
        pages += 1
        if progress:
            progress(f"polymarket: page {pages}")
        yield from events
        cursor = data.get("next_cursor")
        if not cursor or not events:
            return


def candidates_from_market(m: dict, event: dict, f: Filters) -> list[Candidate]:
    if m.get("closed") or not m.get("active", True) or m.get("acceptingOrders") is False:
        return []
    end = parse_time(m.get("endDate") or event.get("endDate"))
    if end is None or end <= f.now or (end - f.now).total_seconds() > f.max_days * 86400:
        return []
    volume = num(m.get("volumeNum")) or num(m.get("volume")) or 0.0
    if volume < f.min_volume:
        return []

    outcomes = json_list(m.get("outcomes")) or ["Yes", "No"]
    prices = [num(p) for p in json_list(m.get("outcomePrices"))]
    tokens = json_list(m.get("clobTokenIds"))
    best_bid, best_ask = num(m.get("bestBid")), num(m.get("bestAsk"))

    # bestBid/bestAsk are quoted for outcome 0. Buying outcome 1 costs (1 - best bid of outcome 0).
    ask0 = best_ask if best_ask else (prices[0] if prices else None)
    ask1 = (1.0 - best_bid) if best_bid else (prices[1] if len(prices) > 1 else None)

    fee_rate = 0.0
    sched = m.get("feeSchedule") or {}
    if m.get("feesEnabled") and sched:
        fee_rate = num(sched.get("rate")) or 0.0

    title = m.get("question") or event.get("title") or m.get("slug", "")
    slug = event.get("slug") or m.get("slug", "")
    flags = []
    status = (m.get("umaResolutionStatus") or "").lower()
    if status in {"proposed", "disputed"}:
        flags.append(f"resolution {status}")
    if m.get("negRisk"):
        flags.append("multi-outcome")

    category = normalize_category([t.get("label") for t in event.get("tags") or []], title)
    out = []
    for idx, ask in ((0, ask0), (1, ask1)):
        if not f.in_band(ask) or idx >= len(outcomes):
            continue
        out.append(Candidate(
            platform=NAME,
            market_id=m.get("conditionId") or str(m.get("id")),
            title=title,
            side=str(outcomes[idx]),
            ask=round(ask, 4),
            end_time=end,
            url=f"https://polymarket.com/event/{slug}",
            volume=volume,
            liquidity=num(m.get("liquidityNum")) or num(m.get("liquidity")) or 0.0,
            fee_rate=fee_rate,
            book_ref=str(tokens[idx]) if idx < len(tokens) else None,
            flags=list(flags),
            category=category,
            event=event.get("title") or "",
        ))
    return out


def scan(f: Filters, progress: Progress | None = None, events: Iterable[dict] | None = None) -> list[Candidate]:
    seen: set[tuple[str, str]] = set()
    out: list[Candidate] = []
    for ev in events if events is not None else iter_events(f, progress):
        for m in ev.get("markets") or []:
            for c in candidates_from_market(m, ev, f):
                key = (c.market_id, c.side)
                if key not in seen:
                    seen.add(key)
                    out.append(c)
    return out


def fetch_book(c: Candidate) -> list[tuple[float, float]]:
    """Ask side for the outcome token: [(price, size)], cheapest first."""
    if not c.book_ref:
        return []
    book = http.get_json(f"{CLOB}/book", {"token_id": c.book_ref})
    levels = [(float(a["price"]), float(a["size"])) for a in book.get("asks") or []]
    return sorted(levels)


def fetch_books(cands: list[Candidate], progress: Progress | None = None) -> dict[str, list[tuple[float, float]]]:
    """Batch version: POST /books takes up to 100 token ids. Returns {token_id: ask levels}."""
    refs = sorted({c.book_ref for c in cands if c.book_ref})
    out: dict[str, list[tuple[float, float]]] = {}
    for i in range(0, len(refs), 100):
        chunk = refs[i:i + 100]
        books = http.post_json(f"{CLOB}/books", [{"token_id": t} for t in chunk])
        for b in books or []:
            levels = [(float(a["price"]), float(a["size"])) for a in b.get("asks") or []]
            out[str(b.get("asset_id"))] = sorted(levels)
        if progress:
            progress(f"polymarket books: {min(i + 100, len(refs))}/{len(refs)}")
    return out
