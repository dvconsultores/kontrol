/**
 * NumberInput — campo numérico (FR-010).
 * Inicia vacío; NO convierte vacío a cero; precisión por dominio.
 * Para dinero usar MoneyInput; nunca flotantes para dinero.
 */
import { clsx } from "clsx";
import { type InputHTMLAttributes, forwardRef } from "react";

export interface NumberInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  invalid?: boolean;
  /** Escala decimal (cantidad de decimales). */
  precision?: number;
}

export const NumberInput = forwardRef<HTMLInputElement, NumberInputProps>(function NumberInput(
  { invalid, precision = 0, className, ...props },
  ref,
) {
  return (
    <input
      ref={ref}
      type="text"
      inputMode="decimal"
      autoComplete="off"
      className={clsx(
        "h-10 w-full rounded-md border bg-surface-0 px-3 text-sm text-text-900 tabular-nums",
        "placeholder:text-text-400",
        invalid
          ? "border-danger-600 focus:border-danger-600 focus:outline-danger-600"
          : "border-border-default focus:border-brand-600 focus:outline-brand-600",
        "disabled:cursor-not-allowed disabled:bg-surface-100 disabled:text-text-400",
        className,
      )}
      aria-invalid={invalid || undefined}
      data-precision={precision}
      {...props}
    />
  );
});
