import { motion } from "motion/react";
import { usd, pct, dur, cents, weekdayDate } from "../lib/format.js";
import { VENUES } from "../config.js";

const median = (xs) => { if (!xs.length) return NaN; const s = [...xs].sort((a, b) => a - b); return s[s.length >> 1]; };

export default function Bento({ rows, total, amount, tbill30, onOpen }) {
  const top = rows[0];
  const beat = rows.filter((r) => r.excess > 0).length;
  const soon = rows.length ? rows.reduce((a, b) => (a.days < b.days ? a : b)) : null;
  const max = top ? Math.max(top.profit, top.tbProfit) : 1;
  return (
    <section className="bento wrap" aria-label="Summary">
      {top && (
        <article className="tile tile-hero glass">
          <h3 className="tile-q">{top.m.t}</h3>
          <p className="tile-meta">
            Today's top pick for {usd(amount, 0)}: buy <b>{top.m.s}</b> at {cents(top.f.avg)} on {VENUES[top.m.v].short}. Pays out {weekdayDate(top.m.endMs)}.
          </p>
          <div className="duel">
            <div>
              <span className="duel-num pos num">+{usd(top.profit)}</span>
              <span className="duel-lab">this market</span>
              <div className="track"><motion.i className="fill-pm" animate={{ width: `${(top.profit / max) * 100}%` }} transition={{ type: "spring", stiffness: 140, damping: 24 }} /></div>
            </div>
            <div>
              <span className="duel-num bill num">+{usd(top.tbProfit)}</span>
              <span className="duel-lab">{top.tb.label} over the same {dur(top.days)}</span>
              <div className="track"><motion.i className="fill-tb" animate={{ width: `${Math.max(0.8, (top.tbProfit / max) * 100)}%` }} transition={{ type: "spring", stiffness: 140, damping: 24 }} /></div>
            </div>
          </div>
          <button className="tile-link" onClick={() => onOpen(top.m.key)}>See the order book and trade</button>
        </article>
      )}
      <article className="tile glass"><b className="num">{rows.length.toLocaleString()}</b><span>markets match your filters, out of {total.toLocaleString()} scanned</span></article>
      <article className="tile glass"><b className="num">{rows.length ? pct(median(rows.map((r) => r.roi)), 2) : "–"}</b><span>median return, about {rows.length ? usd(median(rows.map((r) => r.profit))) : "$0"} per {usd(amount, 0)}</span></article>
      <article className="tile glass"><b className="num">{rows.length ? pct(beat / rows.length, 0) : "–"}</b><span>out-earn T-bills over the same days, after fees</span></article>
      <article className="tile glass"><b className="num">{soon ? dur(soon.days) : "–"}</b><span>until the next one pays out. T-bills yield {pct(tbill30.rate, 2)} today.</span></article>
    </section>
  );
}
