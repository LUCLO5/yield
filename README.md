# Yield

**Prediction markets, priced like bonds.** Yield finds markets priced at 95–99¢ and shows what they'd actually pay you, after fees and slippage, versus T-bills.

(The Python package and CLI are still called `pmscan`.)

## pmscan: the scanner

Scans **Polymarket US**, **Kalshi** and **Polymarket (international)** for outcomes priced at **96%+** and works out what you'd actually earn if you put in a given amount, after fees and slippage, compared to the same money sitting in **T-bills** for the same length of time.

```
$ python -m pmscan --amount 1000

pmscan 0.1.0 · 2026-11-18 18:00 UTC · stake $1,000 per market · ask 96.0%–99.5% · resolving within 30d
Benchmark: T-bills 1M 4.10%, 3M 4.34%, 6M 4.42%, 1Y 4.62% (FRED, 2026-11-16)
1382 opportunities from kalshi, polymarket (1491 quotes matched, 80 order books checked) in 63s

 #  Venue  Market                                                   Buy  Price  Days  Profit/$1,000    ROI  Annual  T-bill  Excess $  1 loss =  Src
--  -----  -------------------------------------------------------  ---  -----  ----  -------------  -----  ------  ------  --------  --------  ----
 1  KX     Austria Wien wins                                        No   0.970   1.1         $28.74  2.88%  941.9%   4.10%    +28.61   35 wins  book
 7  PM     Will Elon Musk post 400-419 tweets from November 13 to…  No   0.962   2.0         $37.31  3.73%  695.5%   4.10%    +37.09   27 wins  book
10  PM     Will the price of Bitcoin be above $58,000 on Novemb…    Yes  0.966   2.0         $32.87  3.29%  612.6%   4.10%    +32.65   30 wins  book
...
```

No API keys. No dependencies beyond the Python standard library.

## Web dashboard

`web/` is a React app (Vite + Motion) with a liquid-glass interface. Think [polybonds.fun](https://www.polybonds.fun/), but for **Polymarket US, Kalshi and international Polymarket**, with real order-book fills, fees and a T-bill comparison.

- **"If I put in $X"** is a live sentence at the top. Every market is re-priced as an exact fill for that amount: the page walks each market's ask levels in your browser, fees included. So $100 and $50k get different (honest) prices.
- Filters: ends (under 24h / week / month / 90 days), minimum price (95–99¢), venue (US venues by default), category and search. Toggles for "beats T-bills" and "fills my whole amount".
- Columns: you make, price, ends, annualized, vs T-bill. Click a row for shares, fees, break-even odds, the order-book ladder and trade links.
- A **Compare** section: a log-scale yield curve of prediction-market median annualized yield by time to resolution against the T-bill curve, with a table view.
- Light / dark / auto appearance and three accent colors (blue, purple, teal).
- A **Start trading** section with referral sign-up links for Polymarket US and Kalshi (set in `web/src/config.js`).

A GitHub Action (`.github/workflows/pages.yml`) runs `python -m pmscan.site` every 30 minutes, builds the app and deploys it to GitHub Pages. No server, no cost.

**One-time setup:** push the repo, then go to **Settings → Pages → Source: GitHub Actions**. Then open the **Actions** tab, pick **refresh site**, and click **Run workflow**. The site goes live at `https://luclo5.github.io/yield/`.

Local development:

```bash
python -m pmscan.site                 # ~2 min: scans all venues + order books -> web/public/data.json
cd web && npm install && npm run dev  # http://localhost:5173
```

> GitHub pauses scheduled workflows after 60 days with no repo activity. If "Updated X ago" goes stale, push any commit or re-run the workflow.

## Install

```bash
git clone https://github.com/LUCLO5/yield.git
cd yield
python -m pmscan --help          # runs straight from the repo (Python 3.9+)

# or install the `pmscan` command
pip install -e .
pmscan -a 2500
```

## Usage

```bash
pmscan -a 1000                                  # $1,000 per market, defaults below
pmscan -a 5000 --min-prob 0.97 --max-days 14    # stricter and shorter
pmscan -a 1000 --beats-tbill --sort excess      # only what out-earns T-bills, ranked by $ edge
pmscan -p kalshi --max-days 90 --csv out.csv    # one venue, longer horizon, export everything
pmscan --min-days 0                             # include markets resolving in the next few hours
pmscan --rf 0.045                               # use a fixed 4.5% instead of the live T-bill curve
```

| Option | Default | What it does |
|---|---|---|
| `-a, --amount` | 1000 | Dollars to put into each market |
| `--min-prob` / `--max-prob` | 0.96 / 0.995 | Price band for the side you'd buy (price ≈ implied probability) |
| `--max-days` / `--min-days` | 30 / 1 | Time-to-resolution window |
| `--min-volume` | 1000 | Skip dead markets |
| `-p, --platform` | all | `polymarket_us`, `kalshi`, `polymarket` |
| `--depth` | 200 | Max order books to check when pricing your exact stake |
| `--allow-partial` | off | Keep markets whose book can't absorb your full stake |
| `--sort` | annual | `annual`, `apy`, `profit`, `excess`, `roi`, `soonest` |
| `--beats-tbill` | off | Only rows that beat T-bills |
| `-n, --top` | 30 | Rows to print |
| `--rf` | live | Fixed risk-free rate instead of FRED T-bill yields |
| `--csv` / `--json` | — | Export all results |

## What the columns mean

| Column | Meaning |
|---|---|
| **Price** | Average fill price for your whole stake (walks the order book, so big stakes pay more) |
| **Profit/$X** | `shares × $1 − (cost + fees)` if the outcome happens |
| **ROI** | Profit ÷ money spent, over the holding period |
| **Annual** | ROI × 365 ÷ days (simple). The CSV also has compounded APY |
| **T-bill** | Yield of the T-bill closest in maturity to the market (1M / 3M / 6M / 1Y) |
| **Excess $** | Profit minus what the same money earns in that T-bill over the same days |
| **1 loss =** | How many of these wins a single wrong call wipes out (`spent ÷ profit`) |
| **Src** | `book` = priced against the live order book; `quote` = best quote only |

The CSV/JSON also includes **break-even win probability** (the true odds you need just to not lose money) and the **break-even vs T-bills** (the odds you need to beat parking the cash).

## How it works

1. **Benchmark:** pulls the latest 1M/3M/6M/1Y Treasury yields from [FRED](https://fred.stlouisfed.org) (`DGS1MO`, `DGS3MO`, `DGS6MO`, `DGS1`).
2. **Scan:** pages through every open market resolving in your window:
   - Polymarket: Gamma API `/events/keyset` (best bid/ask, end date, fee schedule).
   - Kalshi: Trade API v2 `/markets` (excludes auto-generated parlay markets).
   - Polymarket US: public gateway `gateway.polymarket.us/v1/events` + per-market books.
3. **Filter:** keeps either side whose **ask** (what you'd actually pay) sits in the probability band.
4. **Price for your stake:** ranks by the quote, then re-prices the leaders against their live order books until it has `--top` markets that can absorb your full amount.
5. **Fees:**
   - Polymarket / Polymarket US taker fee: `shares × rate × p × (1 − p)`, using each market's own rate (`feeRate` / `feeCoefficient`).
   - Kalshi taker fee: `0.07 × contracts × P × (1 − P)`, rounded up to the cent, whole contracts only.

## The catch (read this)

Buying at 96¢ means you're **betting the market is right, or slightly too pessimistic**. The table assumes every bet wins.

- **The downside isn't symmetric.** Win and you make ~4%. Lose and you lose ~100%. At 96¢ one loss erases about 25 wins. The `1 loss =` column exists so you don't forget.
- **You only profit if the true probability is above the break-even.** A market priced at 96% that really happens 95% of the time loses money over many bets. Favorite–longshot research suggests favorites are often *slightly* underpriced, but it's a thin edge. Prove it with a track record before sizing up.
- **Huge annualized numbers mostly come from short markets.** 2% in 2 days annualizes to 400%+ only if you can redeploy the full stake every 2 days into equally good bets. You usually can't.
- **The end date isn't the payout date.** Polymarket resolutions go through UMA and can be disputed. Kalshi markets can settle after `close_time`. Your money is tied up until settlement.
- **"Probability" here is just a price.** The data includes sports, weather, crypto strikes and tweet counts. Some are near-certain; some are 96% because of a mispriced or illiquid book.
- **Taxes and access differ.** T-bill interest is state-tax-exempt; prediction market gains generally aren't treated as interest. Check which venues are legal for you (e.g. Polymarket's international exchange vs. Polymarket US).

This is a research tool, not financial advice.

## Development

```bash
pip install pytest
pytest -q
```

Layout:

```
pmscan/
  cli.py            # terminal scanner
  site.py           # builds web/public/data.json for the dashboard (batch order books)
  calc.py           # order-book fill simulation + yield math
  fees.py           # Polymarket & Kalshi fee formulas
  benchmark.py      # T-bill curve from FRED
  output.py         # table / CSV / JSON
  http.py           # stdlib HTTP with gzip + retry/backoff
  sources/
    polymarket.py
    kalshi.py
    polymarket_us.py
web/                # React dashboard (src/lib/calc.js mirrors calc.py)
.github/workflows/  # tests + scheduled Pages deploy
tests/
```

Ideas: a `--watch` mode that re-scans on an interval, alerts (email/Discord) for new matches, logging results to track how 96%+ markets actually resolve over time (that last one tells you whether there's an edge at all).

## License

MIT
