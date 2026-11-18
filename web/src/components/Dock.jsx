import { ButtonGroup, ButtonGroupText, ToggleGroup } from "./ui/button-group.jsx";
import { Button } from "./ui/button.jsx";
import { Switch } from "./ui/switch.jsx";

export const ENDS = [["day", "Under 24h", 0, 1], ["week", "This week", 1, 7], ["month", "This month", 1, 30], ["q", "90 days", 1, 90]];
export const MINP = [[0.95, "95¢+"], [0.96, "96¢+"], [0.97, "97¢+"], [0.98, "98¢+"], [0.99, "99¢+"]];
export const VENUE_OPTS = [["us", "US venues"], ["pu", "Polymarket US"], ["kx", "Kalshi"], ["pm", "International"]];
export const SORTS = [["annual", "Annualized"], ["profit", "You make"], ["excess", "Beats T-bill by"], ["roi", "Return"], ["ends", "Ends"], ["depth", "Liquidity"]];

export default function Dock({ s, set }) {
  return (
    <div className="dock glass">
      <div className="dock-row">
        <ToggleGroup label="Ends" options={ENDS.map(([v, t]) => [v, t])} value={s.ends} onChange={(v) => set({ ends: v })} />
        <ToggleGroup label="Minimum price" options={MINP} value={s.minp} onChange={(v) => set({ minp: v })} />
        <ToggleGroup label="Venue" options={VENUE_OPTS} value={s.venue} onChange={(v) => set({ venue: v })} />
      </div>
      <div className="dock-row">
        <ButtonGroup className="grow" aria-label="Search">
          <input className="input-ui" placeholder="Search markets" value={s.q} onChange={(e) => set({ q: e.target.value })} aria-label="Search markets" />
          <Button variant="outline" size="icon" aria-label="Clear search" isDisabled={!s.q} onPress={() => set({ q: "" })}>×</Button>
        </ButtonGroup>
        <ButtonGroup aria-label="Sort">
          <ButtonGroupText>Sort by</ButtonGroupText>
          <select className="select-ui" value={s.sort} aria-label="Sort by"
            onChange={(e) => set({ sort: e.target.value, dir: e.target.value === "ends" ? 1 : -1 })}>
            {SORTS.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
          </select>
          <Button variant="outline" size="icon" aria-label={s.dir < 0 ? "Sorted high to low" : "Sorted low to high"}
            onPress={() => set({ dir: -s.dir })}>{s.dir < 0 ? "↓" : "↑"}</Button>
        </ButtonGroup>
        <Switch isSelected={s.beats} onChange={(v) => set({ beats: v })}>Beats T-bills</Switch>
        <Switch isSelected={s.full} onChange={(v) => set({ full: v })}>Fills my whole amount</Switch>
      </div>
    </div>
  );
}
