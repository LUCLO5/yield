import { Switch as AriaSwitch } from "react-aria-components";

export function Switch({ children, isSelected, onChange }) {
  return (
    <AriaSwitch className="switch-ui" isSelected={isSelected} onChange={onChange}>
      <span className="switch-track"><span className="switch-thumb" /></span>
      {children}
    </AriaSwitch>
  );
}
