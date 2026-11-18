import { AnimatePresence, motion } from "motion/react";
import { usd, pct, cents, dur, shortDate, compact } from "../lib/format.js";
import { VENUES, REFERRALS } from "../config.js";
import { ButtonGroup, ButtonGroupSeparator } from "./ui/button-group.jsx";
import { Button } from "./ui/button.jsx";

const COLS = [
  ["q", "Market", null], ["side", "Side", null], ["make", "You make", "profit"], ["price", "Price", null],
  ["ends", "Ends", "ends"], ["ann", "Annualized", "annual"], ["vs", "vs T-bill", "excess"],
];
const sideClass = (s) => { const l = s.toLowerCase(); return l === "yes" ? "yes" : l === "no" ? "no" : "other"; };

function Detail({ r }) {
  const { m, f } = r;
  const maxSize = Math.max(...m.lv.map(([p, z]) => p * z));
  const ref = REFERRALS[m.v];
  return (
    <motion.div className="detail" initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }}
      exit={{ height: 0, opacity: 0 }} transition={{ type: "spring", stiffness: 300, damping: 34 }}>
      <div className="detail-in">
        <div>
          <dl className="facts num">
            <div><dt>Shares you get</dt><dd>{f.shares.toLocaleString("en-US", { maximumFractionDigits: 2 })}</dd></div>
            <div><dt>Cost plus fees</dt><dd>{usd(f.cost)} + {usd(f.fee)}</dd></div>
            <div><dt>Paid out if right</dt><dd className="pos">{usd(f.shares)}</dd></div>
            <div><dt>Lost if wrong</dt><dd className="neg">−{usd(f.spent)}</dd></div>
            <div><dt>One loss erases</dt><dd>{isFinite(r.lossWins) ? `${Math.round(r.lossWins)} wins like this` : "–"}</dd></div>
            <div><dt>Break-even odds</dt><dd>{pct(r.breakeven, 2)}</dd></div>
            <div><dt>Odds needed to beat T-bills</dt><dd>{pct(r.breakevenTb, 2)}</dd></div>
            <div><dt>{r.tb.label}, same {dur(r.days)}</dt><dd className="bill">{usd(r.tbProfit)} at {pct(r.tb.rate, 2)}</dd></div>
            <div><dt>Resolves</dt><dd>{new Date(m.endMs).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" })}</dd></div>
          </dl>
          <div className="actions">
            <ButtonGroup aria-label="Trade">
              <Button href={m.url} target="_blank" rel="noopener">Trade on {VENUES[m.v].short} ↗</Button>
              {ref && <><ButtonGroupSeparator /><Button href={ref} target="_blank" rel="noopener sponsored">Sign up</Button></>}
            </ButtonGroup>
            {ref && <span className="actions-note">Sign up uses my referral link.</span>}
          </div>
        </div>
        <div className="book num">
          <div className="ladder">
            {m.lv.slice(0, 8).map(([p, z], i) => (
              <div key={i} className={i < f.used ? "used" : ""}>
                <span>{cents(p)}</span>
                <i style={{ width: `${Math.max(3, ((p * z) / maxSize) * 100)}%` }} />
                <span>{usd(p * z, 0)}</span>
              </div>
            ))}
          </div>
          <p className="ladder-note">The asks you'd buy from, cheapest first. Highlighted levels fill your {usd(f.spent, 0)}. Volume {compact(m.vol)}.</p>
        </div>
      </div>
    </motion.div>
  );
}

export default function MarketSheet({ rows, shown, open, setOpen, sort, dir, onSort, onMore }) {
  if (!rows.length) {
    return <div className="sheet glass"><div className="empty">No markets match. Try a lower minimum price, a longer window, or a smaller amount.</div></div>;
  }
  return (
    <>
      <div className="sheet glass" role="table" aria-label="Markets">
        <div className="head" role="row">
          {COLS.map(([k, label, key]) => (
            <span key={k} className={`c-${k}`} role="columnheader">
              {key ? <button aria-pressed={sort === key} onClick={() => onSort(key)}>{label}{sort === key ? (dir < 0 ? " ↓" : " ↑") : ""}</button> : label}
            </span>
          ))}
        </div>
        {rows.slice(0, shown).map((r) => {
          const { m, f } = r;
          const isOpen = open === m.key;
          return (
            <div key={m.key} className={`item${isOpen ? " open" : ""}`} role="rowgroup">
              <div className="row" role="row" tabIndex={0} aria-expanded={isOpen}
                onClick={() => setOpen(isOpen ? null : m.key)}
                onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), setOpen(isOpen ? null : m.key))}>
                <div className="c-q">
                  <div className="q">{m.t}</div>
                  <div className="tags">
                    <span className="venue" style={{ color: VENUES[m.v].color }}>{VENUES[m.v].short}</span>
                    <span>{m.c}</span>
                    <span className="mobile-meta"><span className={`side ${sideClass(m.s)}`}>{m.s}</span> ends in {dur(r.days)}</span>
                    {(m.fl || []).map((x) => <span key={x} className="flag">{x}</span>)}
                  </div>
                </div>
                <div className="c-side"><span className={`side ${sideClass(m.s)}`} title={m.s}>{m.s}</span></div>
                <div className="c-make num"><span className="make">+{usd(r.profit)}</span>
                  {!f.complete && <span className="sub warn">fills {usd(f.spent, 0)} only</span>}</div>
                <div className="c-price num">{cents(f.avg)}{f.used > 1 && <span className="sub">best {cents(m.lv[0][0])}</span>}</div>
                <div className="c-ends num">{dur(r.days)}<span className="sub">{shortDate(m.endMs)}</span></div>
                <div className="c-ann num"><span className="ann">{pct(r.annual, r.annual >= 10 ? 0 : 1)}</span>
                  <span className="sub">{pct(r.roi, 2)} return</span></div>
                <div className="c-vs num"><span className={r.excess > 0 ? "vs-pos" : "vs-neg"}>{r.excess > 0 ? "+" : ""}{usd(r.excess)}</span>
                  <span className="sub">bill pays {usd(r.tbProfit)}</span></div>
              </div>
              <AnimatePresence initial={false}>{isOpen && <Detail r={r} />}</AnimatePresence>
            </div>
          );
        })}
      </div>
      {rows.length > shown && (
        <Button variant="outline" className="more" onPress={onMore}>Show {Math.min(50, rows.length - shown)} more of {(rows.length - shown).toLocaleString()}</Button>
      )}
    </>
  );
}
