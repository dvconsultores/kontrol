/**
 * TextInput — campo de texto (FR-009/FR-013).
 * Los identificadores (RIF, cédula, teléfono, código, serial, IMEI,
 * cuenta) se tratan como texto y conservan ceros iniciales.
 */
import { clsx } from "clsx";
import { type InputHTMLAttributes, forwardRef } from "react";

export interface TextInputProps extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
}

export const TextInput = forwardRef<HTMLInputElement, TextInputProps>(function TextInput(
  { invalid, className, ...props },
  ref,
) {
  return (
    <input
      ref={ref}
      className={clsx(
        "h-10 w-full rounded-md border bg-surface-0 px-3 text-sm text-text-900",
        "placeholder:text-text-400",
        invalid
          ? "border-danger-600 focus:border-danger-600 focus:outline-danger-600"
          : "border-border-default focus:border-brand-600 focus:outline-brand-600",
        "disabled:cursor-not-allowed disabled:bg-surface-100 disabled:text-text-400",
        className,
      )}
      aria-invalid={invalid || undefined}
      {...props}
    />
  );
});
