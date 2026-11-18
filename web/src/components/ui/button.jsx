import { Button as AriaButton, Link } from "react-aria-components";

const cx = (...c) => c.filter(Boolean).join(" ");

/** variant: default | outline | ghost; size: sm | (default) | lg | icon */
export function Button({ variant = "default", size, className, href, ...props }) {
  const cls = cx("btn-ui", variant, size, className);
  if (href) return <Link href={href} className={cls} {...props} />;
  return <AriaButton className={cls} {...props} />;
}
