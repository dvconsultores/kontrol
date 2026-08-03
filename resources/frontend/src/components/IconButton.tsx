/**
 * IconButton — botón de solo icono con aria-label y tooltip (FR-014).
 * Usa Lucide; el icono nunca sustituye el nombre accesible.
 */
import { clsx } from "clsx";
import { type ButtonHTMLAttributes, forwardRef } from "react";

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  /** Lucide icon component. */
  icon: React.ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
  variant?: "default" | "danger";
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { label, icon: Icon, variant = "default", className, type = "button", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      aria-label={label}
      title={label}
      className={clsx(
        "inline-flex size-9 items-center justify-center rounded-md transition-colors",
        variant === "danger"
          ? "text-danger-600 hover:bg-danger-100"
          : "text-text-500 hover:bg-surface-100 hover:text-text-900",
        "disabled:cursor-not-allowed disabled:text-text-400",
        className,
      )}
      {...props}
    >
      <Icon className="size-4" aria-hidden={true} />
    </button>
  );
});
