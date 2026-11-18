// shadcn/ui "aria" ButtonGroup, built on react-aria-components.
// Buttons inside a group share borders; only the outer corners are rounded.
import { Group, ToggleButton, ToggleButtonGroup, Separator } from "react-aria-components";

const cx = (...c) => c.filter(Boolean).join(" ");

export function ButtonGroup({ className, orientation = "horizontal", ...props }) {
  return <Group data-orientation={orientation} className={cx("bg", className)} {...props} />;
}

export function ButtonGroupSeparator({ className }) {
  return <Separator orientation="vertical" className={cx("bg-sep", className)} />;
}

export function ButtonGroupText({ className, ...props }) {
  return <span className={cx("bg-text", className)} {...props} />;
}

/** Single-select toggle group (filters, appearance). value/onChange use plain keys. */
export function ToggleGroup({ label, options, value, onChange, size, className }) {
  return (
    <ToggleButtonGroup
      aria-label={label}
      selectionMode="single"
      disallowEmptySelection
      selectedKeys={new Set([String(value)])}
      onSelectionChange={(keys) => {
        const k = [...keys][0];
        const match = options.find(([v]) => String(v) === k);
        if (match) onChange(match[0]);
      }}
      className={cx("bg", className)}
    >
      {options.map(([v, text]) => (
        <ToggleButton key={String(v)} id={String(v)} className={cx("btn-ui outline", size)}>{text}</ToggleButton>
      ))}
    </ToggleButtonGroup>
  );
}
