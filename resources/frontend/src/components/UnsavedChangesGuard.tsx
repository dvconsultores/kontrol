/**
 * UnsavedChangesGuard — protección de cambios sin guardar (FR-024).
 * Confirma antes de abandonar la ruta, refrescar o cerrar la pestaña.
 */
import { useEffect, useState } from "react";
import { useBlocker } from "react-router";

export interface UnsavedChangesGuardProps {
  hasUnsavedChanges: boolean;
}

export function UnsavedChangesGuard({ hasUnsavedChanges }: UnsavedChangesGuardProps): React.JSX.Element | null {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [proceed, setProceed] = useState(false);

  const blocker = useBlocker(({ currentLocation, nextLocation }) => {
    if (proceed) {
      return false;
    }
    return hasUnsavedChanges && currentLocation.pathname !== nextLocation.pathname;
  });

  useEffect(() => {
    if (blocker?.state === "blocked") {
      setDialogOpen(true);
    } else {
      setDialogOpen(false);
    }
  }, [blocker?.state]);

  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent): void => {
      if (hasUnsavedChanges) {
        e.preventDefault();
      }
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [hasUnsavedChanges]);

  if (!dialogOpen) {
    return null;
  }

  return (
    <div
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="unsaved-title"
      className="fixed inset-0 z-70 flex items-center justify-center bg-text-900/50 p-4"
    >
      <div className="w-full max-w-md rounded-lg bg-surface-0 p-6 shadow-lg">
        <h2 id="unsaved-title" className="text-lg font-semibold text-text-900">
          ¿Descartar los cambios sin guardar?
        </h2>
        <p className="mt-2 text-sm text-text-500">
          Hay cambios sin guardar en esta pantalla. Si continúa, los perderá.
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            className="h-10 rounded-md border border-border-default px-4 text-sm font-medium text-text-700 hover:bg-surface-100"
            onClick={() => {
              setDialogOpen(false);
              blocker?.reset?.();
            }}
          >
            Permanecer
          </button>
          <button
            type="button"
            className="h-10 rounded-md bg-danger-600 px-4 text-sm font-medium text-white hover:bg-danger-700"
            onClick={() => {
              setDialogOpen(false);
              setProceed(true);
              blocker?.proceed?.();
            }}
          >
            Descartar cambios
          </button>
        </div>
      </div>
    </div>
  );
}
