/**
 * FormField — envoltorio de campo de formulario (FR-009).
 * Label visible, error con borde rojo + mensaje, aria-invalid y
 * aria-describedby. Requerido con indicador semántico.
 * Inyecta `id`, `aria-invalid` y `aria-describedby` al hijo.
 */
import { cloneElement, isValidElement, useId, type ReactElement, type ReactNode } from "react";

import { clsx } from "clsx";

export interface FormFieldProps {
  label: string;
  htmlFor?: string;
  required?: boolean;
  error?: string;
  help?: string;
  children: ReactNode;
  className?: string;
}

export function FormField({
  label,
  htmlFor,
  required,
  error,
  help,
  children,
  className,
}: FormFieldProps): React.JSX.Element {
  const autoId = useId();
  const fieldId = htmlFor ?? autoId;
  const errorId = `${fieldId}-error`;
  const helpId = `${fieldId}-help`;

  const child = isValidElement(children)
    ? cloneElement(children as ReactElement<Record<string, unknown>>, {
        id: fieldId,
        "aria-invalid": error ? true : undefined,
        "aria-describedby": [error ? errorId : null, help ? helpId : null].filter(Boolean).join(" ") || undefined,
      })
    : children;

  return (
    <div className={clsx("flex flex-col gap-1.5", className)}>
      <label htmlFor={fieldId} className="text-sm font-medium text-text-700">
        {label}
        {required ? <span aria-hidden="true" className="text-danger-600"> *</span> : null}
        {required ? <span className="sr-only"> (obligatorio)</span> : null}
      </label>
      {child}
      {help ? (
        <p id={helpId} className="text-xs text-text-500">
          {help}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} className="text-sm text-danger-600" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
