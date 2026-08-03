/**
 * DateInput — campo de fecha (FR-012 §9.4).
 * El valor viaja como ISO (fecha); el formato de pantalla es independiente.
 * La zona horaria se controla; el servidor es autoridad para emisión/licencia.
 */
import { clsx } from "clsx";
import { type InputHTMLAttributes, forwardRef } from "react";

export interface DateInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  invalid?: boolean;
}

export const DateInput = forwardRef<HTMLInputElement, DateInputProps>(function DateInput(
  { invalid, className, ...props },
  ref,
) {
  return (
    <input
      ref={ref}
      type="date"
      className={clsx(
        "h-10 w-full rounded-md border bg-surface-0 px-3 text-sm text-text-900",
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
