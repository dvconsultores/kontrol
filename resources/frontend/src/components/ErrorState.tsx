/** ErrorState — error recuperable con Reintentar y request ID (DOC-08 §11). */
import { AlertTriangle } from "lucide-react";

import { Button } from "./Button";

export interface ErrorStateProps {
  title?: string;
  message: string;
  requestId?: string;
  onRetry?: () => void;
}

export function ErrorState({
  title = "No fue posible completar la operación",
  message,
  requestId,
  onRetry,
}: ErrorStateProps): React.JSX.Element {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-danger-100 bg-danger-100/40 px-6 py-10 text-center">
      <AlertTriangle className="size-10 text-danger-600" aria-hidden="true" />
      <h3 className="text-base font-medium text-text-900">{title}</h3>
      <p className="max-w-md text-sm text-text-500">{message}</p>
      {requestId ? <p className="text-xs text-text-400">ID de solicitud: {requestId}</p> : null}
      {onRetry ? (
        <Button variant="secondary" onClick={onRetry} className="mt-2">
          Reintentar
        </Button>
      ) : null}
    </div>
  );
}
