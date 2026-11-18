import { useEffect, useState } from "react";
import { motion, useMotionValue, useSpring } from "motion/react";

const INTERACTIVE = "a, button, select, label, [role='button'], [role='switch'], .row";
const TEXT = "input:not([type='checkbox']), textarea";

/**
 * A quiet cursor: a precise accent dot plus a thin ring that follows tightly
 * and fills in slightly over clickable things. Fine pointers only; off for reduced motion.
 */
export default function Cursor() {
  const [enabled, setEnabled] = useState(false);
  const [state, setState] = useState("idle"); // idle | hover | text | down | hidden
  const x = useMotionValue(-100), y = useMotionValue(-100);
  const rx = useSpring(x, { stiffness: 1100, damping: 60, mass: 0.35 });
  const ry = useSpring(y, { stiffness: 1100, damping: 60, mass: 0.35 });

  useEffect(() => {
    const fine = window.matchMedia("(pointer: fine)");
    const calm = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setEnabled(fine.matches && !calm.matches);
    update();
    fine.addEventListener("change", update); calm.addEventListener("change", update);
    return () => { fine.removeEventListener("change", update); calm.removeEventListener("change", update); };
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("custom-cursor", enabled);
    if (!enabled) return;
    let down = false;
    const move = (e) => {
      x.set(e.clientX); y.set(e.clientY);
      if (down) return;
      const t = e.target instanceof Element ? e.target : null;
      setState(t?.closest(TEXT) ? "text" : t?.closest(INTERACTIVE) ? "hover" : "idle");
    };
    const press = () => { down = true; setState("down"); };
    const release = (e) => { down = false; move(e); };
    const leave = () => setState("hidden");
    window.addEventListener("pointermove", move, { passive: true });
    window.addEventListener("pointerdown", press);
    window.addEventListener("pointerup", release);
    document.addEventListener("pointerleave", leave);
    return () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerdown", press);
      window.removeEventListener("pointerup", release);
      document.removeEventListener("pointerleave", leave);
      document.documentElement.classList.remove("custom-cursor");
    };
  }, [enabled, x, y]);

  if (!enabled) return null;
  const ring = { idle: 22, hover: 30, text: 0, down: 18, hidden: 0 }[state];
  return (
    <>
      <motion.div className={`cursor-ring${state === "hover" ? " on" : ""}`} aria-hidden="true" style={{ x: rx, y: ry }}
        animate={{ width: ring, height: ring, opacity: ring ? 1 : 0 }} transition={{ duration: 0.18, ease: [0.32, 0.72, 0, 1] }} />
      <motion.div className="cursor-dot" aria-hidden="true" style={{ x, y }}
        animate={{ opacity: state === "text" || state === "hidden" ? 0 : 1 }} transition={{ duration: 0.12 }} />
    </>
  );
}
