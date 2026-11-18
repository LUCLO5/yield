import { useLayoutEffect, useRef } from "react";
import { motion } from "motion/react";
import { usd, weekdayDate } from "../lib/format.js";


export default function Hero({ amountText, setAmountText, amount, setAmount, top }) {
  const input = useRef(null);
  // Size the input to its own text so the number never clips, in any font or browser.
  useLayoutEffect(() => {
    const el = input.current;
    if (!el) return;
    const fit = () => { el.style.width = "0px"; el.style.width = `${el.scrollWidth + 2}px`; };
    fit();
    document.fonts?.ready.then(fit);
    window.addEventListener("resize", fit);
    return () => window.removeEventListener("resize", fit);
  }, [amountText]);
  const max = top ? Math.max(top.profit, top.tbProfit) : 1;
  return (
    <section className="hero wrap" aria-labelledby="hero-sentence">
      <h1 className="sentence" id="hero-sentence">
        <span className="soft">If I put in </span>
        <span className="nowrap"><label className="lens lg">
          <span>$</span>
          <input
            ref={input}
            aria-label="Amount to put in"
            inputMode="decimal"
            value={amountText}
            onChange={(e) => {
              const raw = e.target.value.replace(/[^0-9.,]/g, "");
              setAmountText(raw);
              const v = parseFloat(raw.replace(/,/g, ""));
              if (v > 0) setAmount(v);
            }}
            onBlur={() => setAmountText(amount.toLocaleString("en-US"))}
            onFocus={(e) => e.target.select()}
          />
        </label><span className="soft">,</span></span>
        {top ? (
          <>
            <span className="soft"> the top pick pays </span>
            <motion.span key={top.profit.toFixed(2)} className="yield-word"
              initial={{ opacity: 0.4, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
              {usd(top.profit)}
            </motion.span>
            <span className="soft"> by {weekdayDate(top.m.endMs)}.</span>
          </>
        ) : (
          <span className="soft"> nothing matches these filters yet.</span>
        )}
      </h1>

      <div className="hero-sub">
        <p>Type any amount. Every figure on this page is a real fill for it: we walk each market's live order book and include the venue's fees.</p>
      </div>

    </section>
  );
}
