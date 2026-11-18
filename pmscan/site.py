"""Build the data file behind the web dashboard.

    python -m pmscan.site            (writes web/public/data.json)

Scans both venues, pulls the live order book for every match (batched, 100 per request),
and writes compact JSON. The page walks those books in the browser, so the
"if I put in $X" numbers are exact fills for any amount, fees included.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from pmscan import __version__, benchmark
from pmscan.models import Candidate
from pmscan.sources import kalshi, polymarket, polymarket_us
from pmscan.sources.common import CATEGORIES, Filters

VENUES = {"polymarket_us": ("pu", polymarket_us), "kalshi": ("kx", kalshi), "polymarket": ("pm", polymarket)}


def book_key(c: Candidate) -> str:
    return str(c.book_ref) if c.platform == "polymarket" else f"{c.book_ref}|{c.side}"


def trim_levels(levels, min_price: float, max_price: float, max_levels: int, max_usd: float):
    """Keep the cheapest asks that are still inside the band, up to a depth cap."""
    out, spent = [], 0.0
    for p, size in sorted(levels):
        if p > max_price or p >= 1 or size <= 0:
            break
        if p < min_price:  # book moved below the band since the quote; still a valid (better) fill
            pass
        out.append([round(p, 4), round(size, 2)])
        spent += p * size
        if len(out) >= max_levels or spent >= max_usd:
            break
    return out


def build(args, log=lambda m: None) -> dict:
    now = datetime.now(timezone.utc)
    f = Filters(min_prob=args.min_prob, max_prob=args.max_prob, max_days=args.max_days,
                min_volume=args.min_volume, now=now)
    curve = benchmark.load_curve(args.rf)

    def run(name: str):
        short, mod = VENUES[name]
        cands = mod.scan(f, log)
        books = mod.fetch_books(cands, log) if cands else {}
        return name, cands, books

    markets, errors = [], []
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(run, n) for n in args.platform]
        for fut in futs:
            try:
                name, cands, books = fut.result()
            except Exception as e:
                errors.append(str(e))
                continue
            short = VENUES[name][0]
            for c in cands:
                lv = trim_levels(books.get(book_key(c), []), args.min_prob, args.max_prob,
                                 args.levels, args.max_depth_usd)
                if not lv or lv[0][0] < args.min_prob:
                    continue  # nobody selling inside the band right now
                if c.volume < args.min_volume:
                    continue  # Polymarket US volume is only known after the book call
                markets.append({
                    "id": c.market_id,
                    "v": short,
                    "t": c.title,
                    "e": c.event,
                    "s": c.side,
                    "c": c.category,
                    "end": c.end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "url": c.url,
                    "vol": round(c.volume),
                    "liq": round(c.liquidity),
                    "fr": c.fee_rate,
                    "kx": c.platform == "kalshi",  # whole contracts, fee rounded up to the cent
                    "lv": lv,
                    "fl": c.flags,
                })

    if errors and not markets:
        raise RuntimeError("; ".join(errors))

    return {
        "version": __version__,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "filters": {"min_prob": args.min_prob, "max_prob": args.max_prob, "max_days": args.max_days,
                    "min_volume": args.min_volume},
        "tbill": {
            "as_of": curve.as_of,
            "fixed": curve.fixed,
            "tenors": [{"label": label, "rate": curve.rates.get(label), "max_days": None if md == float("inf") else md}
                       for label, _, md in benchmark.TENORS if label in curve.rates],
        },
        "categories": CATEGORIES,
        "errors": errors,
        "markets": markets,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="pmscan.site", description="Build data.json for the web dashboard")
    p.add_argument("--out", default="web/public/data.json")
    p.add_argument("--min-prob", type=float, default=0.95)
    p.add_argument("--max-prob", type=float, default=0.995)
    p.add_argument("--max-days", type=float, default=90)
    p.add_argument("--min-volume", type=float, default=1000)
    p.add_argument("--levels", type=int, default=25, help="max ask levels kept per market")
    p.add_argument("--max-depth-usd", type=float, default=250_000, help="stop keeping levels past this much depth")
    p.add_argument("--rf", type=float, default=None)
    p.add_argument("-p", "--platform", nargs="+", choices=sorted(VENUES), default=sorted(VENUES))
    p.add_argument("-q", "--quiet", action="store_true")
    args = p.parse_args(argv)

    def log(m):
        if not args.quiet:
            print(f"\r\033[K{m}", end="", file=sys.stderr, flush=True)

    t0 = time.time()
    data = build(args, log)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, separators=(",", ":")))
    log("")
    print(f"wrote {len(data['markets'])} markets to {out} ({out.stat().st_size / 1e6:.1f} MB) in {time.time() - t0:.0f}s"
          + (f"; errors: {data['errors']}" if data["errors"] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
