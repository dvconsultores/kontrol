/** ConflictState — conflicto concurrente (409); no sobrescritura silenciosa (FR-030). */
import { RefreshCw } from "lucide-react";

import { Button } from "./Button";

export interface ConflictStateProps {
  message?: string;
  onReload?: () => void;
}

export function ConflictState({
  message = "Otro usuario modificó este registro mientras trabajaba. No se guardaron sus cambios para evitar sobrescribir los datos.",
  onReload,
}: ConflictStateProps): React.JSX.Element {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-warning-100 bg-warning-100/40 px-6 py-10 text-center">
      <RefreshCw className="size-10 text-warning-600" aria-hidden="true" />
      <h3 className="text-base font-medium text-text-900">Conflicto de concurrencia</h3>
      <p className="max-w-md text-sm text-text-500">{message}</p>
      {onReload ? (
        <Button variant="secondary" onClick={onReload} className="mt-2">
          Recargar datos
        </Button>
      ) : null}
    </div>
  );
}
