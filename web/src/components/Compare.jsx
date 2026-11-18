import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { evaluate, tbillFor, DAY } from "../lib/calc.js";
import { pct, usd } from "../lib/format.js";
import { ToggleGroup } from "./ui/button-group.jsx";

// Time-to-resolution buckets (days). Each becomes one point on the prediction-market curve.
const BUCKETS = [
  [0, 1, "Under a day"], [1, 3, "1–3 days"], [3, 7, "3–7 days"], [7, 14, "1–2 weeks"],
  [14, 30, "2–4 weeks"], [30, 60, "1–2 months"], [60, 90, "2–3 months"],
];
const X_TICKS = [[1 / 24, "1h"], [1, "1d"], [3, "3d"], [7, "1w"], [14, "2w"], [30, "1m"], [90, "3m"]];
const Y_TICKS = [0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30];

const median = (xs) => { if (!xs.length) return NaN; const s = [...xs].sort((a, b) => a - b); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
const mult = (a, b) => { const r = a / b; return r >= 10 ? Math.round(r).toLocaleString() : r.toFixed(1); };
const yLabel = (v) => (v >= 1 ? `${(v * 100).toLocaleString("en-US")}%` : `${+(v * 100).toFixed(0)}%`);

function useWidth() {
  const ref = useRef(null);
  const [w, setW] = useState(800);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width));
    ro.observe(el); return () => ro.disconnect();
  }, []);
  return [ref, w];
}

export default function Compare({ data, amount, venue, minp, full }) {
  const [metric, setMetric] = useState("annual");
  const [view, setView] = useState("chart");
  const [hover, setHover] = useState(null);
  const [wrapRef, width] = useWidth();

  const { buckets, dots } = useMemo(() => {
    const now = Date.now();
    const venueOk = venue === "us" ? (v) => v === "pu" || v === "kx" : (v) => v === venue;
    const rows = [];
    for (const m of data.markets) {
      if (!venueOk(m.v) || m.lv[0][0] < minp - 1e-9) continue;
      const days = (m.endMs - now) / DAY;
      if (days <= 1 / 24 || days > 90) continue;
      const r = evaluate(m, amount, now, data.tbill);
      if (!r || r.profit <= 0 || (full && !r.f.complete)) continue;
      rows.push(r);
    }
    const buckets = BUCKETS.map(([lo, hi, label]) => {
      const inB = rows.filter((r) => r.days > lo && r.days <= hi);
      if (!inB.length) return null;
      const d = median(inB.map((r) => r.days));
      const tb = tbillFor(data.tbill, d);
      return {
        label, n: inB.length, days: d,
        annual: median(inB.map((r) => r.annual)), roi: median(inB.map((r) => r.roi)),
        profit: median(inB.map((r) => r.profit)), tb: tb.rate, tbLabel: tb.label,
        tbProfit: amount * tb.rate * d / 365, beat: inB.filter((r) => r.excess > 0).length / inB.length,
      };
    }).filter(Boolean);
    // Thin the scatter so the chart stays light: at most ~900 dots, evenly sampled.
    const step = Math.max(1, Math.ceil(rows.length / 900));
    const dots = rows.filter((_, i) => i % step === 0).map((r) => ({ days: r.days, annual: r.annual, roi: r.roi }));
    return { buckets, dots };
  }, [data, amount, venue, minp, full]);

  // ----- scales (log-log for annualized; log-x / linear-y for per-trade return) -----
  const H = width < 600 ? 300 : 380;
  const M = { t: 24, r: width < 600 ? 16 : 150, b: 36, l: 52 };
  const iw = Math.max(100, width - M.l - M.r), ih = H - M.t - M.b;
  const xMin = 1 / 24, xMax = 90;
  const x = (d) => M.l + ((Math.log(Math.max(d, xMin)) - Math.log(xMin)) / (Math.log(xMax) - Math.log(xMin))) * iw;

  const isAnnual = metric === "annual";
  const pmVal = (b) => (isAnnual ? b.annual : b.roi);
  const tbVal = (b) => (isAnnual ? b.tb : b.tb * b.days / 365);
  const dotVal = (d) => (isAnnual ? d.annual : d.roi);
  const allVals = [...buckets.flatMap((b) => [pmVal(b), tbVal(b)]), ...dots.map(dotVal)].filter((v) => v > 0);
  const yLo = isAnnual ? 0.01 : Math.max(1e-5, Math.min(...allVals) / 1.6);
  const yHi = isAnnual ? Math.min(30, Math.max(0.3, Math.max(...allVals) * 1.4)) : Math.max(...allVals) * 1.2;
  const y = (v) => M.t + ih - ((Math.log(Math.max(v, yLo)) - Math.log(yLo)) / (Math.log(yHi) - Math.log(yLo))) * ih;
  const yTicks = isAnnual ? Y_TICKS.filter((t) => t >= yLo && t <= yHi)
    : [0.0001, 0.0003, 0.001, 0.003, 0.01, 0.03, 0.1].filter((t) => t >= yLo && t <= yHi);

  const path = (fn) => buckets.map((b, i) => `${i ? "L" : "M"}${x(b.days).toFixed(1)},${y(fn(b)).toFixed(1)}`).join(" ");
  // T-bill curve: step through tenors across the whole x range, not just bucket points.
  const tbPath = useMemo(() => {
    const pts = [];
    for (let i = 0; i <= 60; i++) {
      const d = Math.exp(Math.log(xMin) + (i / 60) * (Math.log(xMax) - Math.log(xMin)));
      const r = tbillFor(data.tbill, d).rate;
      pts.push([x(d), y(isAnnual ? r : r * d / 365)]);
    }
    return pts.map(([a, b], i) => `${i ? "L" : "M"}${a.toFixed(1)},${b.toFixed(1)}`).join(" ");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, width, isAnnual, yLo, yHi]);

  const last = buckets[buckets.length - 1];
  const first = buckets[0];
  const onMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const px = e.clientX - rect.left;
    let best = null, dist = Infinity;
    buckets.forEach((b, i) => { const dd = Math.abs(x(b.days) - px); if (dd < dist) { dist = dd; best = i; } });
    setHover(best);
  };
  const hb = hover != null ? buckets[hover] : null;
  const shortest = buckets[0], longest = buckets[buckets.length - 1];

  return (
    <section className="compare wrap" id="compare" aria-labelledby="compare-title">
      <h2 className="section-title" id="compare-title">Prediction markets vs. T-bills</h2>
      <p className="section-lede">The same money, the same number of days. Each point is the median market resolving in that window, priced for {usd(amount, 0)}.</p>

      {shortest && longest && (
        <div className="compare-facts">
          <div className="glass"><b className="num">{mult(shortest.annual, shortest.tb)}×</b><span>the T-bill rate for markets ending {shortest.label.toLowerCase()}</span></div>
          <div className="glass"><b className="num">{mult(longest.annual, longest.tb)}×</b><span>for markets {longest.label === "2–3 months" ? "two to three months out" : longest.label.toLowerCase() + " out"}{longest.annual / longest.tb < 2 ? ", about what a T-bill pays" : ""}</span></div>
          <div className="glass"><b className="num">{pct(median(buckets.map((b) => b.roi)), 2)}</b><span>median return per trade, before you redeploy the money</span></div>
        </div>
      )}

      <div className="chart-card glass">
        <div className="chart-bar">
          <div className="legend" aria-hidden={view === "table"}>
            <span><i className="sw-pm" />Prediction markets, median</span>
            <span><i className="sw-tb" />US Treasury bills</span>
          </div>
          <div className="chart-ctl">
            <ToggleGroup label="Measure" size="sm" options={[["annual", "Annualized"], ["trade", "Per trade"]]} value={metric} onChange={setMetric} />
            <ToggleGroup label="View" size="sm" options={[["chart", "Chart"], ["table", "Table"]]} value={view} onChange={setView} />
          </div>
        </div>

        {view === "chart" ? (
          <div ref={wrapRef} className="chart-wrap" onPointerMove={onMove} onPointerLeave={() => setHover(null)}>
            {!buckets.length ? <div className="empty">No markets match these filters.</div> : (
              <svg width={width} height={H} role="img"
                aria-label={`Line chart: prediction-market ${isAnnual ? "annualized yield" : "return per trade"} by time to resolution, compared with T-bills. Use the table view for exact values.`}>
                {yTicks.map((t) => (
                  <g key={t}>
                    <line className="grid" x1={M.l} x2={M.l + iw} y1={y(t)} y2={y(t)} />
                    <text className="tick" x={M.l - 10} y={y(t)} dy="0.32em" textAnchor="end">{isAnnual ? yLabel(t) : `${+(t * 100).toPrecision(2)}%`}</text>
                  </g>
                ))}
                {X_TICKS.map(([d, l]) => (
                  <text key={l} className="tick" x={x(d)} y={M.t + ih + 22} textAnchor="middle">{l}</text>
                ))}
                <text className="axis-title" x={M.l + iw} y={M.t + ih + 22} dx={width < 600 ? 0 : 14} textAnchor="start">{width < 600 ? "" : "until it pays"}</text>

                {dots.filter((d) => dotVal(d) <= yHi && dotVal(d) >= yLo).map((d, i) => (
                  <circle key={i} className="dot" cx={x(d.days)} cy={y(dotVal(d))} r="2.2" />
                ))}

                <motion.path className="line-tb" d={tbPath} initial={false} animate={{ d: tbPath }} transition={{ duration: 0.5 }} />
                <motion.path className="line-pm" d={path(pmVal)} initial={false} animate={{ d: path(pmVal) }} transition={{ duration: 0.5 }} />
                {buckets.map((b, i) => (
                  <circle key={b.label} className={`mk-pm${hover === i ? " on" : ""}`} cx={x(b.days)} cy={y(pmVal(b))} r={hover === i ? 6 : 4.5} />
                ))}

                {width >= 600 && last && (() => {
                  const tbEnd = isAnnual ? tbillFor(data.tbill, xMax).rate : tbillFor(data.tbill, xMax).rate * xMax / 365;
                  let yp = y(pmVal(last)), yt = y(tbEnd);
                  if (Math.abs(yp - yt) < 16) { const mid = (yp + yt) / 2, up = pmVal(last) >= tbEnd; yp = mid + (up ? -9 : 9); yt = mid + (up ? 9 : -9); }
                  return (<>
                    <text className="dlabel" x={M.l + iw + 12} y={yp} dy="0.32em">Prediction markets</text>
                    <text className="dlabel" x={M.l + iw + 12} y={yt} dy="0.32em">T-bills</text>
                  </>);
                })()}

                {hb && <line className="crosshair" x1={x(hb.days)} x2={x(hb.days)} y1={M.t} y2={M.t + ih} />}
              </svg>
            )}
            <AnimatePresence>
              {hb && (
                <motion.div className="tip glass" initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                  transition={{ duration: 0.12 }}
                  style={{ left: Math.min(Math.max(x(hb.days) - 110, 8), width - 228), top: Math.max(8, y(pmVal(hb)) - 150) }}>
                  <strong>Ends {hb.label.toLowerCase()}</strong>
                  <div><i className="sw-pm" />Markets<span className="num">{isAnnual ? pct(hb.annual, 0) : pct(hb.roi, 2)}</span></div>
                  <div><i className="sw-tb" />{hb.tbLabel}<span className="num">{isAnnual ? pct(hb.tb, 2) : pct(hb.tb * hb.days / 365, 3)}</span></div>
                  <div className="tip-foot">{usd(hb.profit)} vs {usd(hb.tbProfit)} on {usd(amount, 0)} · {hb.n} markets</div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data-table num">
              <thead><tr><th>Ends</th><th>Markets</th><th>Median annualized</th><th>T-bill</th><th>Multiple</th><th>Median you make</th><th>T-bill makes</th><th>Beat T-bills</th></tr></thead>
              <tbody>
                {buckets.map((b) => (
                  <tr key={b.label}>
                    <td>{b.label}</td><td>{b.n.toLocaleString()}</td><td>{pct(b.annual, 0)}</td><td>{pct(b.tb, 2)} <small>{b.tbLabel}</small></td>
                    <td>{mult(b.annual, b.tb)}×</td><td>{usd(b.profit)}</td><td>{usd(b.tbProfit)}</td><td>{pct(b.beat, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="chart-note">Log scale. Annualized figures assume you could roll the money into an equally good market as soon as each one pays, which is rarely possible, and that every market resolves the way it's priced. The T-bill line is the 1-month, 3-month and 6-month yield from FRED.</p>
      </div>
    </section>
  );
}
