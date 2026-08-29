/**
 * ConfirmationDialog — confirmación breve (ADR-015).
 * Solo para confirmar desactivar/eliminar/anular/reversar/descartar y alertas.
 * Loader dentro del botón Confirmar (FR-007); no abre un segundo modal.
 */
import { type ReactNode, useEffect, useRef } from "react";
import { createPortal } from "react-dom";

import { AsyncButton } from "./AsyncButton";
import { Button } from "./Button";

export interface ConfirmationDialogProps {
  open: boolean;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  /**
   * Contenido breve dentro de la confirmación (por ejemplo, el motivo
   * obligatorio de un rechazo). No convierte el modal en un formulario
   * complejo: eso sigue exigiendo pantalla completa (ADR-015 / P18).
   */
  children?: ReactNode;
  onConfirm: () => Promise<void>;
  onCancel: () => void;
}

export function ConfirmationDialog({
  open,
  title,
  description,
  confirmLabel = "Confirmar",
  cancelLabel = "Cancelar",
  danger,
  children,
  onConfirm,
  onCancel,
}: ConfirmationDialogProps): React.JSX.Element | null {
  const confirmRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open) {
      confirmRef.current?.focus();
      const onKey = (e: KeyboardEvent): void => {
        if (e.key === "Escape") {
          onCancel();
        }
      };
      document.addEventListener("keydown", onKey);
      return () => document.removeEventListener("keydown", onKey);
    }
    return undefined;
  }, [open, onCancel]);

  if (!open) {
    return null;
  }

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
      className="fixed inset-0 z-70 flex items-center justify-center bg-text-900/50 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onCancel();
        }
      }}
    >
      <div className="w-full max-w-md rounded-lg bg-surface-0 p-6 shadow-lg">
        <h2 id="dialog-title" className="text-lg font-semibold text-text-900">
          {title}
        </h2>
        {description ? <p className="mt-2 text-sm text-text-500">{description}</p> : null}
        {children ? <div className="mt-4">{children}</div> : null}
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="secondary" onClick={onCancel}>
            {cancelLabel}
          </Button>
          <AsyncButton variant={danger ? "danger" : "primary"} onClick={onConfirm} loadingText="Confirmando…">
            {confirmLabel}
          </AsyncButton>
        </div>
      </div>
    </div>,
    document.body,
  );
}
