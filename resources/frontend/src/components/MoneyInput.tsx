/**
 * MoneyInput — campo de dinero (FR-012).
 * Etiquetas neutrales; la moneda es un indicador dinámico (nunca
 * hardcodear Bs/VES/USD en labels). El valor viaja como string decimal.
 */
import { clsx } from "clsx";
import { type InputHTMLAttributes, forwardRef } from "react";

export interface MoneyInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  invalid?: boolean;
  /** Código ISO de la moneda mostrada como indicador (no en el label). */
  currency?: string;
}

export const MoneyInput = forwardRef<HTMLInputElement, MoneyInputProps>(function MoneyInput(
  { invalid, currency, className, ...props },
  ref,
) {
  return (
    <div className="relative">
      <input
        ref={ref}
        type="text"
        inputMode="decimal"
        autoComplete="off"
        className={clsx(
          "h-10 w-full rounded-md border bg-surface-0 px-3 text-sm text-text-900 tabular-nums",
          currency ? "pr-12" : "",
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
      {currency ? (
        <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs font-medium text-text-500">
          {currency}
        </span>
      ) : null}
    </div>
  );
});
