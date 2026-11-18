import { useEffect, useMemo, useState, useDeferredValue } from "react";
import { motion } from "motion/react";
import { evaluate, tbillFor, DAY } from "./lib/calc.js";
import { REPO_URL, BRAND } from "./config.js";
import { useTheme } from "./lib/theme.js";
import Cursor from "./components/Cursor.jsx";
import Menu from "./components/Menu.jsx";
import Hero from "./components/Hero.jsx";
import Bento from "./components/Bento.jsx";
import Compare from "./components/Compare.jsx";
import Dock, { ENDS } from "./components/Dock.jsx";
import MarketSheet from "./components/MarketSheet.jsx";
import Trade from "./components/Trade.jsx";
import How from "./components/How.jsx";

const SORT_KEY = {
  annual: (r) => r.annual, profit: (r) => r.profit, excess: (r) => r.excess, roi: (r) => r.roi,
  ends: (r) => r.days, depth: (r) => r.m.depth,
};

function useData() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    fetch("data.json", { cache: "no-cache" })
      .then((r) => { if (!r.ok) throw new Error(`data.json returned ${r.status}`); return r.json(); })
      .then((d) => {
        d.markets.forEach((m, i) => {
          m.endMs = Date.parse(m.end);
          m.key = `${m.v}-${i}`;
          m.search = `${m.t} ${m.e || ""} ${m.s} ${m.c}`.toLowerCase();
          m.depth = m.lv.reduce((s, [p, z]) => s + p * z, 0);
        });
        setData(d);
      })
      .catch((e) => setError(e.message));
  }, []);
  return [data, error];
}

export default function App() {
  const [data, error] = useData();
  const theme = useTheme();
  const [amount, setAmount] = useState(1000);
  const [amountText, setAmountText] = useState("1,000");
  const [s, setS] = useState({ ends: "month", minp: 0.96, venue: "us", q: "", sort: "annual", dir: -1, beats: false, full: true, cat: "All" });
  const [shown, setShown] = useState(50);
  const [open, setOpen] = useState(null);
  const set = (patch) => { setS((x) => ({ ...x, ...patch })); setShown(50); };

  const dAmount = useDeferredValue(amount);
  const dq = useDeferredValue(s.q.trim().toLowerCase());

  // Everything except category, so the tabs can show counts.
  const matched = useMemo(() => {
    if (!data) return [];
    const now = Date.now();
    const [, , lo, hi] = ENDS.find((e) => e[0] === s.ends);
    const venueOk = s.venue === "us" ? (v) => v === "pu" || v === "kx" : (v) => v === s.venue;
    const out = [];
    for (const m of data.markets) {
      if (!venueOk(m.v)) continue;
      const days = (m.endMs - now) / DAY;
      if (days <= 0 || days < lo || days > hi) continue;
      if (m.lv[0][0] < s.minp - 1e-9) continue;
      if (dq && !m.search.includes(dq)) continue;
      const r = evaluate(m, dAmount, now, data.tbill);
      if (!r || r.profit <= 0) continue;
      if (s.full && !r.f.complete) continue;
      if (s.beats && r.excess <= 0) continue;
      out.push(r);
    }
    return out;
  }, [data, s.ends, s.minp, s.venue, s.full, s.beats, dq, dAmount]);

  const rows = useMemo(() => {
    const list = s.cat === "All" ? [...matched] : matched.filter((r) => r.m.c === s.cat);
    const k = SORT_KEY[s.sort];
    return list.sort((a, b) => s.dir * (k(a) - k(b)));
  }, [matched, s.cat, s.sort, s.dir]);

  const catCounts = useMemo(() => {
    const c = { All: matched.length };
    for (const r of matched) c[r.m.c] = (c[r.m.c] || 0) + 1;
    return c;
  }, [matched]);

  const venueCounts = useMemo(() => {
    const c = {};
    if (data) for (const m of data.markets) c[m.v] = (c[m.v] || 0) + 1;
    return c;
  }, [data]);

  const onSort = (k) => set(s.sort === k ? { dir: -s.dir } : { sort: k, dir: k === "ends" ? 1 : -1 });

  return (
    <>
      <div className="field" aria-hidden="true"><i /><i /><i /></div>

      <Cursor />
      <header className="nav">
        <div className="nav-in">
          <a className="mark" href="#top" aria-label={`${BRAND.name} home`}><span className="orb" /><b>{BRAND.wordmark}</b></a>
          <Menu theme={theme} />
        </div>
      </header>

      <main id="top">
        {error && <div className="wrap"><div className="sheet glass"><div className="empty">Couldn't load market data ({error}). Refresh the page, or check the latest run in the repo's Actions tab.</div></div></div>}

        <Hero amount={amount} setAmount={(v) => { setAmount(v); setShown(50); }} amountText={amountText} setAmountText={setAmountText}
          top={rows[0]} />

        {data && (
          <>
          <Bento rows={rows} total={data.markets.length} amount={amount} tbill30={tbillFor(data.tbill, 30)}
            onOpen={(k) => { setOpen(k); document.getElementById("markets")?.scrollIntoView({ behavior: "smooth" }); }} />
          <Compare data={data} amount={dAmount} venue={s.venue} minp={s.minp} full={s.full} />
          <div className="wrap markets" id="markets">
            <h2 className="section-title">Every market, priced for you</h2>
            <p className="section-lede">Filter by when it pays, how sure the market is and where you can trade it. Tap any market for the full fill.</p>
            <Dock s={s} set={set} />
            <div className="cats" role="group" aria-label="Category">
              {["All", ...data.categories].filter((c) => catCounts[c]).map((c) => (
                <button key={c} aria-pressed={s.cat === c} onClick={() => set({ cat: c })}>
                  {s.cat === c && <motion.span layoutId="cat-thumb" className="thumb" transition={{ type: "spring", stiffness: 420, damping: 34 }} />}
                  {c}<small>{catCounts[c]}</small>
                </button>
              ))}
            </div>
            <MarketSheet rows={rows} shown={shown} open={open} setOpen={setOpen} sort={s.sort} dir={s.dir}
              onSort={onSort} onMore={() => setShown((n) => n + 50)} />
          </div>
          </>
        )}

        <Trade counts={venueCounts} />
        <How />
      </main>

      <footer className="wrap">
        <span>{BRAND.name}. Data from the Polymarket US, Kalshi and Polymarket public APIs; T-bill yields from FRED. Open source on <a href={REPO_URL} target="_blank" rel="noopener">GitHub</a>.</span>
        <span>Not financial advice. Check which venues are available where you live.</span>
      </footer>
    </>
  );
}
