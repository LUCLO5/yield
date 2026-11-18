export const usd = (x, d = 2) =>
  (x < 0 ? "−$" : "$") + Math.abs(x).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
export const pct = (x, d = 1) =>
  isFinite(x) ? (x * 100).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }) + "%" : "∞";
export const cents = (p) => { const c = p * 100; return (Math.abs(c - Math.round(c)) > 1e-6 ? c.toFixed(1) : Math.round(c)) + "¢"; };
export const dur = (d) => (d < 1 ? Math.max(1, Math.round(d * 24)) + "h" : d < 10 ? d.toFixed(1) + "d" : Math.round(d) + "d");
export const shortDate = (ms) => new Date(ms).toLocaleDateString("en-US", { month: "short", day: "numeric" });
export const weekdayDate = (ms) => {
  const d = new Date(ms), now = new Date();
  const diff = (d - now) / 864e5;
  if (diff < 1 && d.getDate() === now.getDate()) return "today";
  if (diff < 2 && d.getDate() === new Date(+now + 864e5).getDate()) return "tomorrow";
  if (diff < 6.5) return d.toLocaleDateString("en-US", { weekday: "long" });
  return d.toLocaleDateString("en-US", { month: "long", day: "numeric" });
};
export const ago = (ms) => {
  const m = Math.round((Date.now() - ms) / 6e4);
  return m < 1 ? "just now" : m < 60 ? `${m} min ago` : `${Math.round(m / 60)}h ago`;
};
export const compact = (x) => x >= 1e6 ? (x / 1e6).toFixed(1) + "M" : x >= 1e3 ? Math.round(x / 1e3) + "k" : String(Math.round(x));
