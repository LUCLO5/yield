import { useEffect, useState } from "react";

export const ACCENTS = [
  { id: "blue", name: "Blue" },
  { id: "purple", name: "Purple" },
  { id: "teal", name: "Teal" },
];

const read = (k, d) => { try { return localStorage.getItem(k) || d; } catch { return d; } };
const write = (k, v) => { try { localStorage.setItem(k, v); } catch { /* storage can be unavailable */ } };

/** mode: "light" | "dark" | "auto"; accent: one of ACCENTS. Applied as data attributes on <html>. */
export function useTheme() {
  const [mode, setMode] = useState(() => read("as-mode", "auto"));
  const [accent, setAccent] = useState(() => read("as-accent", "blue"));

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const resolved = mode === "auto" ? (mq.matches ? "dark" : "light") : mode;
      document.documentElement.dataset.theme = resolved;
      document.querySelector('meta[name="theme-color"]')?.setAttribute("content", resolved === "dark" ? "#000000" : "#f5f5f7");
    };
    apply();
    write("as-mode", mode);
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [mode]);

  useEffect(() => {
    document.documentElement.dataset.accent = accent;
    write("as-accent", accent);
  }, [accent]);

  return { mode, setMode, accent, setAccent };
}
