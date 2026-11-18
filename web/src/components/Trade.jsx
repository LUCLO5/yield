import { REFERRALS } from "../config.js";
import { Button } from "./ui/button.jsx";

export default function Trade({ counts }) {
  const cards = [
    {
      v: "pu", name: "Polymarket US", tint: "var(--pu)", cta: "Open a Polymarket US account",
      points: [
        "The US version of Polymarket, with deposits and payouts in dollars.",
        "Taker fee is the market's fee coefficient × shares × p × (1 − p). Near 97¢ that's a fraction of a cent per share.",
        "Listings are separate from international Polymarket, so trade the markets tagged Polymarket US here.",
      ],
    },
    {
      v: "kx", name: "Kalshi", tint: "var(--kx)", cta: "Open a Kalshi account",
      points: [
        "A CFTC-regulated US exchange with dollar deposits.",
        "Taker fee is 0.07 × contracts × p × (1 − p), rounded up to the cent. Whole contracts only.",
        "Lots of short-dated markets: sports, weather, crypto and economic data.",
      ],
    },
  ];
  return (
    <section className="trade wrap" id="trade" aria-labelledby="trade-title">
      <h2 className="section-title" id="trade-title">Start trading</h2>
      <p className="section-lede">Both venues below are open to US traders. Pick one, fund it, then use the list above to find markets priced like short-term bonds.</p>
      <div className="venues">
        {cards.map((c) => (
          <article key={c.v} className="venue-card glass">
            <div className="tint" style={{ background: c.tint }} />
            <h3>{c.name}</h3>
            <p style={{ margin: 0, color: "var(--ink-2)" }}>
              <span className="count num">{(counts[c.v] || 0).toLocaleString()}</span> markets at 95¢ or more right now.
            </p>
            <ul>{c.points.map((p) => <li key={p}>{p}</li>)}</ul>
            <Button size="lg" href={REFERRALS[c.v]} target="_blank" rel="noopener sponsored">{c.cta} ↗</Button>
          </article>
        ))}
      </div>
      <p className="disclose">These are my referral links. If you sign up through them I may get a bonus; it doesn't change your fees or anything this page shows.</p>
    </section>
  );
}
