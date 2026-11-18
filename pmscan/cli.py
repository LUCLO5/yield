"""Command-line entry point.

    python -m pmscan --amount 1000
    python -m pmscan -a 5000 --min-prob 0.97 --max-days 14 --csv results.csv
"""

from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from datetime import datetime, timezone

from pmscan import __version__, benchmark, calc, fees, output
from pmscan.models import Candidate, Result
from pmscan.sources import SOURCES, kalshi, polymarket, polymarket_us
from pmscan.sources.common import Filters

SORT_KEYS = {
    "annual": lambda r: r.simple_annual,
    "apy": lambda r: r.apy,
    "profit": lambda r: r.profit,
    "excess": lambda r: r.excess_vs_tbill,
    "roi": lambda r: r.roi,
    "soonest": lambda r: -r.days,
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pmscan",
        description="Scan Polymarket and Kalshi for outcomes priced at high probability "
                    "and compare the return on your stake to T-bills.",
    )
    p.add_argument("-a", "--amount", type=float, default=1000, help="dollars to put in each market (default 1000)")
    p.add_argument("--min-prob", type=float, default=0.96, help="minimum ask price / implied probability (default 0.96)")
    p.add_argument("--max-prob", type=float, default=0.995,
                   help="maximum ask price (default 0.995; above this there's almost nothing left to earn)")
    p.add_argument("--max-days", type=float, default=30, help="only markets resolving within N days (default 30)")
    p.add_argument("--min-days", type=float, default=1,
                   help="skip markets resolving sooner than N days (default 1; 0 includes intraday markets, "
                        "whose annualized numbers get absurd)")
    p.add_argument("--min-volume", type=float, default=1000, help="minimum lifetime volume (default 1000)")
    p.add_argument("-p", "--platform", nargs="+", choices=sorted(SOURCES), default=sorted(SOURCES),
                   help="which venues to scan (default: both)")
    p.add_argument("--depth", type=int, default=200,
                   help="max order books to check: results are re-priced against the live book for your exact "
                        "stake until --top rows survive (default 200, 0 = quotes only)")
    p.add_argument("--allow-partial", action="store_true",
                   help="keep markets whose book can't absorb your whole stake (dropped by default)")
    p.add_argument("--sort", choices=sorted(SORT_KEYS), default="annual", help="sort order (default annual)")
    p.add_argument("--beats-tbill", action="store_true", help="only show markets that out-earn T-bills")
    p.add_argument("-n", "--top", type=int, default=30, help="rows to print (default 30)")
    p.add_argument("--rf", type=float, default=None,
                   help="fixed risk-free rate as a decimal (e.g. 0.043). Default: live T-bill curve from FRED")
    p.add_argument("--kalshi-fee-rate", type=float, default=fees.KALSHI_TAKER_RATE,
                   help="Kalshi taker fee multiplier (default 0.07)")
    p.add_argument("--csv", help="write all results to this CSV file")
    p.add_argument("--json", help="write all results to this JSON file")
    p.add_argument("-q", "--quiet", action="store_true", help="no progress output")
    p.add_argument("--version", action="version", version=f"pmscan {__version__}")
    return p


def _log(quiet: bool):
    def log(msg: str) -> None:
        if not quiet:
            print(f"\r\033[K{msg}", end="", file=sys.stderr, flush=True)
    return log


def gather(args, f: Filters, log) -> tuple[list[Candidate], list[str]]:
    errors: list[str] = []
    cands: list[Candidate] = []

    def run(name: str) -> list[Candidate]:
        if name == "kalshi":
            return kalshi.scan(f, log, fee_rate=args.kalshi_fee_rate)
        if name == "polymarket_us":
            cands = polymarket_us.scan(f, log)
            polymarket_us.fetch_books(cands, log)  # volume comes from book stats
            return [c for c in cands if c.volume >= f.min_volume]
        return polymarket.scan(f, log)

    with ThreadPoolExecutor(max_workers=len(args.platform)) as ex:
        futs = {ex.submit(run, name): name for name in args.platform}
        for fut in as_completed(futs):
            try:
                cands.extend(fut.result())
            except Exception as e:  # keep going if one venue is down
                errors.append(f"{futs[fut]}: {e}")
    return cands, errors


def _reprice_one(r: Result, stake: float, curve, now) -> Result | None:
    c = r.cand
    try:
        levels = SOURCES[c.platform].fetch_book(c)
    except Exception:
        return r  # keep the quote-based estimate if the book call fails
    if not levels:
        return None  # nobody is selling this side right now
    fill = calc.simulate_fill(levels, stake, c.fee_rate, round_up_cent=c.fee_round_cent,
                              whole_shares=c.platform == "kalshi")
    return calc.evaluate(c, stake, replace(fill, from_book=True), now, curve)


def reprice_with_books(results: list[Result], budget: int, want: int, stake: float, curve, now,
                       min_prob: float, allow_partial: bool, key) -> tuple[list[Result], int]:
    """Walk down the ranking, pricing each candidate against its live book, until `want` rows
    survive or `budget` books have been fetched. Returns (results, books_checked)."""
    checked: list[Result] = []
    i = 0
    batch = 40
    while i < min(budget, len(results)):
        chunk = results[i: min(i + batch, budget)]
        with ThreadPoolExecutor(max_workers=8) as ex:
            for r in ex.map(lambda x: _reprice_one(x, stake, curve, now), chunk):
                if r is None:
                    continue
                # Book moved below the threshold since the quote, or can't absorb the stake.
                if r.fill.from_book and r.fill.avg_price < min_prob - 1e-9:
                    continue
                if not allow_partial and not r.fill.complete:
                    continue
                checked.append(r)
        i += len(chunk)
        if sum(1 for r in checked if r.profit > 0) >= want:
            break
    rest = [r for r in results[i:] if allow_partial or r.fill.complete]
    checked.sort(key=key, reverse=True)
    return checked + rest, i


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 0 < args.min_prob < 1 or not args.min_prob <= args.max_prob < 1:
        print("--min-prob and --max-prob must be between 0 and 1, with min <= max.", file=sys.stderr)
        return 2
    log = _log(args.quiet)
    now = datetime.now(timezone.utc)
    f = Filters(min_prob=args.min_prob, max_prob=args.max_prob, max_days=args.max_days,
                min_volume=args.min_volume, now=now)

    t0 = time.time()
    log("fetching T-bill yields…")
    try:
        curve = benchmark.load_curve(args.rf)
    except RuntimeError as e:
        print(f"\n{e}", file=sys.stderr)
        return 1

    cands, errors = gather(args, f, log)
    cands = [c for c in cands if (c.end_time - now).total_seconds() >= args.min_days * 86400]

    results = [r for c in cands if (r := calc.evaluate(c, args.amount, calc.top_of_book_fill(c, args.amount), now, curve))]
    key = SORT_KEYS[args.sort]
    results.sort(key=key, reverse=True)

    if args.beats_tbill:
        results = [r for r in results if r.excess_vs_tbill > 0]
    books = 0
    if args.depth and results:
        log("checking order books…")
        results, books = reprice_with_books(results, args.depth, args.top, args.amount, curve, now,
                                            args.min_prob, args.allow_partial, key)
    elif not args.allow_partial:
        results = [r for r in results if r.fill.complete]
    if args.beats_tbill:
        results = [r for r in results if r.excess_vs_tbill > 0]
    results = [r for r in results if r.profit > 0]

    log("")
    print(f"pmscan {__version__} · {now:%Y-%m-%d %H:%M} UTC · stake ${args.amount:,.0f} per market · "
          f"ask {args.min_prob:.1%}–{args.max_prob:.1%} · resolving within {args.max_days:g}d")
    print(f"Benchmark: {curve.describe()}")
    print(f"{len(results)} opportunities from {', '.join(args.platform)} "
          f"({len(cands)} quotes matched, {books} order books checked) in {time.time() - t0:.0f}s\n")
    for e in errors:
        print(f"! {e}", file=sys.stderr)

    if results:
        print(output.table(results[: args.top], args.amount))
        print("\nProfit/ROI assume the outcome resolves as priced. 'Excess $' = profit minus what the same money "
              "earns in a T-bill over the same days.\n'1 loss =' is how many of these wins a single wrong call wipes out. "
              "'quote' rows use top-of-book only; 'book' rows are priced for your full stake.")
    else:
        print("Nothing matched. Try widening --max-days or lowering --min-volume.")

    if args.csv:
        output.write_csv(results, args.csv)
        print(f"\nWrote {len(results)} rows to {args.csv}")
    if args.json:
        output.write_json(results, args.json)
        print(f"Wrote {len(results)} rows to {args.json}")
    return 0
