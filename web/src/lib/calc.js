// Mirrors pmscan/calc.py exactly (verified against it in CI-style checks).
const DAY = 864e5;

export const feePerShare = (p, r) => r * p * (1 - p);

/** Spend `stake` (fees included) walking cheapest-first ask levels [[price, size], ...]. */
export function fill(levels, stake, r, kx) {
  let remaining = stake, shares = 0, cost = 0, feeRaw = 0, used = 0;
  for (const [p, size] of levels) {
    if (remaining <= 0) break;
    const allIn = p + feePerShare(p, r);
    let take = Math.min(size, remaining / allIn);
    if (kx) take = Math.floor(take + 1e-9);
    if (take <= 0) break;
    used++; shares += take; cost += take * p; feeRaw += take * feePerShare(p, r);
    remaining -= take * allIn;
    if (take < size) break;
  }
  let fee = kx && feeRaw > 0 ? Math.ceil(feeRaw * 100 - 1e-9) / 100 : feeRaw;
  if (kx && shares > 0 && cost + fee > stake + 1e-9) {
    const avg = cost / shares;
    while (shares > 0 && cost + fee > stake + 1e-9) {
      shares -= 1; cost = shares * avg;
      fee = Math.ceil(r * shares * avg * (1 - avg) * 100 - 1e-9) / 100;
    }
  }
  const spent = cost + fee;
  return { shares, cost, fee, spent, used, avg: shares ? cost / shares : 0,
           complete: stake - spent < Math.max(1, 0.01 * stake) };
}

export function tbillFor(tbill, days) {
  if (tbill.fixed != null) return { rate: tbill.fixed, label: "Fixed rate" };
  for (const t of tbill.tenors) if (t.max_days == null || days <= t.max_days) return t;
  return tbill.tenors[tbill.tenors.length - 1];
}

export function evaluate(m, stake, now, tbill) {
  const f = fill(m.lv, stake, m.fr, m.kx);
  if (f.shares <= 0) return null;
  const days = Math.max((m.endMs - now) / DAY, 1e-6);
  const profit = f.shares - f.spent;
  const roi = profit / f.spent;
  const tb = tbillFor(tbill, days);
  const tbProfit = f.spent * tb.rate * days / 365;
  return {
    m, f, days, profit, roi, annual: (roi * 365) / days, tb, tbProfit, excess: profit - tbProfit,
    breakeven: f.spent / f.shares, breakevenTb: (f.spent + tbProfit) / f.shares,
    lossWins: profit > 0 ? f.spent / profit : Infinity,
  };
}

export { DAY };
