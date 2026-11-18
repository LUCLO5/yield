import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ToggleGroup } from "./ui/button-group.jsx";
import { Button } from "./ui/button.jsx";
import { ACCENTS } from "../lib/theme.js";
import { REPO_URL } from "../config.js";

const LINKS = [["#compare", "Compare"], ["#markets", "Markets"], ["#trade", "Trade"], ["#how", "How it works"]];

export default function Menu({ theme }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const away = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false);
    const esc = (e) => e.key === "Escape" && setOpen(false);
    document.addEventListener("pointerdown", away);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("pointerdown", away); document.removeEventListener("keydown", esc); };
  }, [open]);

  return (
    <div className="menu" ref={ref}>
      <button className="menu-btn glass" aria-expanded={open} aria-controls="site-menu" aria-label={open ? "Close menu" : "Open menu"}
        onClick={() => setOpen((o) => !o)}>
        <span className={`burger${open ? " x" : ""}`}><i /><i /></span>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div id="site-menu" className="menu-panel glass" role="menu"
            initial={{ opacity: 0, scale: 0.94, y: -8 }} animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -6 }} transition={{ type: "spring", stiffness: 520, damping: 36 }}>
            <nav className="menu-links">
              {LINKS.map(([href, label]) => (
                <a key={href} href={href} role="menuitem" onClick={() => setOpen(false)}>{label}</a>
              ))}
              <a href={REPO_URL} target="_blank" rel="noopener" role="menuitem">GitHub <span aria-hidden="true">↗</span></a>
            </nav>
            <div className="menu-row">
              <span>Appearance</span>
              <ToggleGroup label="Appearance" size="sm" options={[["light", "Light"], ["dark", "Dark"], ["auto", "Auto"]]}
                value={theme.mode} onChange={theme.setMode} />
            </div>
            <div className="menu-row">
              <span>Accent</span>
              <div className="swatches" role="radiogroup" aria-label="Accent color">
                {ACCENTS.map((a) => (
                  <button key={a.id} role="radio" aria-checked={theme.accent === a.id} aria-label={a.name}
                    className={`swatch sw-${a.id}`} onClick={() => theme.setAccent(a.id)} />
                ))}
              </div>
            </div>
            <Button href="#trade" className="wide" onPress={() => setOpen(false)}>Start trading</Button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
