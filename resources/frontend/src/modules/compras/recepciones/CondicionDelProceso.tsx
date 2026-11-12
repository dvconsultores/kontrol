/**
 * Condición del proceso de la recepción (Spec 018 · §3).
 *
 * No es un estado del inventario: la deriva el backend de la recepción, de su
 * confirmación (Spec 021) y de las incidencias vivas (Spec 020). Por eso aquí
 * no se recalcula nada —ni etiqueta ni precedencia—: se muestra el texto que
 * publica el backend, de modo que Recepciones y el expediente digan lo mismo.
 */
import { Link } from "react-router";

import type { ReceiptProcessCondition } from "@/api/types";

type Props = {
  condicion: ReceiptProcessCondition | null | undefined;
  /** Recepción concreta, para llevar a sus incidencias existentes. */
  receiptId: string;
  /** Expediente desde el que se muestra, si aplica, para volver a él. */
  importacionId?: string;
};

const TONO: Record<ReceiptProcessCondition["code"], string> = {
  RECIBIDO: "border-success-200 bg-success-50 text-success-700",
  PENDIENTE_DE_VALIDACION: "border-border-default bg-surface-100 text-text-700",
  BLOQUEADO_POR_INCIDENCIA: "border-danger-200 bg-danger-50 text-danger-700",
};

export function CondicionDelProceso({ condicion, receiptId, importacionId }: Props): React.JSX.Element {
  if (!condicion) {
    return <span className="text-sm text-text-500">—</span>;
  }
  const bloqueada = condicion.code === "BLOQUEADO_POR_INCIDENCIA";
  const incidencias = `/compras/incidencias?recepcion=${encodeURIComponent(receiptId)}${
    importacionId ? `&importacion=${encodeURIComponent(importacionId)}` : ""
  }`;
  return (
    <div className="flex flex-col items-start gap-1">
      <span
        className={`inline-flex w-fit items-center rounded-md border px-2 py-0.5 text-xs font-medium ${TONO[condicion.code]}`}
        data-condicion={condicion.code}
      >
        {condicion.label}
      </span>
      {condicion.reason ? <span className="text-xs text-text-600">{condicion.reason}</span> : null}
      {bloqueada ? (
        <Link to={incidencias} className="text-xs font-medium text-brand-600 hover:text-brand-700">
          Ver {condicion.blocking_incidents === 1 ? "la incidencia" : "las incidencias"}
        </Link>
      ) : null}
    </div>
  );
}
