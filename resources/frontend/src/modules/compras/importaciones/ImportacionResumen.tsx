import { useState } from "react";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { apiFetch, ApiError } from "@/api/client";
import { ESTADOS, ETAPAS_LOGISTICAS } from "./tipos";
import type { DetalleImportacion } from "./ImportacionDetallePage";

type Props = {
  detalle: DetalleImportacion;
  onCambios: () => void;
};

export function ImportacionResumen({ detalle, onCambios }: Props) {
  const [error, setError] = useState<string | null>(null);

  const confirmarDespacho = async () => {
    setError(null);
    try {
      await apiFetch(`/importaciones/${detalle.id}/confirm-dispatch`, {
        method: "POST",
      });
      onCambios();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409 && err.details?.missing) {
        setError("Falta registrar la salida real");
      } else {
        setError(
          err instanceof Error ? err.message : "Error al confirmar despacho.",
        );
      }
    }
  };

  return (
    <section
      id="resumen"
      className="rounded-lg border border-border-default bg-surface-0 p-6"
    >
      <h2 className="mb-4 text-lg font-semibold text-text-900">Resumen</h2>
      <dl className="grid gap-4 md:grid-cols-2">
        <div>
          <dt className="text-sm text-text-600">Estado</dt>
          <dd>{ESTADOS[detalle.status]}</dd>
        </div>
        <div>
          <dt className="text-sm text-text-600">Siguiente paso</dt>
          <dd>{detalle.next_action ?? "Sin siguiente acción."}</dd>
        </div>
        {detalle.status === "CANCELLED" && detalle.cancel_reason && (
          <div className="md:col-span-2">
            <dt className="text-sm text-text-600">Motivo de cancelación</dt>
            <dd className="mt-1 text-text-600">{detalle.cancel_reason}</dd>
          </div>
        )}
        {detalle.summary.pending.length === 0 ? (
          <div className="md:col-span-2">
            <dt className="text-sm text-text-600">Pendientes</dt>
            <dd className="mt-1">Sin pendientes</dd>
          </div>
        ) : (
          <div className="md:col-span-2">
            <dt className="text-sm text-text-600">Pendientes</dt>
            <dd className="mt-1">
              <ul className="list-inside list-disc">
                {detalle.summary.pending.map((pendiente) => (
                  <li key={pendiente}>{pendiente}</li>
                ))}
              </ul>
            </dd>
          </div>
        )}
        <div>
          <dt className="text-sm text-text-600">Documentos validados</dt>
          <dd>
            {detalle.summary.documents_validated} / {detalle.summary.documents_required}
          </dd>
        </div>
        <div>
          <dt className="text-sm text-text-600">Correcciones abiertas</dt>
          <dd>{detalle.summary.open_corrections}</dd>
        </div>
        <div>
          <dt className="text-sm text-text-600">Documentos financieros</dt>
          <dd>{detalle.summary.financial_count}</dd>
        </div>
        <div>
          <dt className="text-sm text-text-600">Agente</dt>
          <dd>{detalle.summary.agent_name ?? "Sin designar"}</dd>
        </div>
        <div>
          <dt className="text-sm text-text-600">Transportista</dt>
          <dd>{detalle.summary.carrier_name ?? "Sin designar"}</dd>
        </div>
        {detalle.logistics ? (
          <div>
            <dt className="text-sm text-text-600">Etapa logística</dt>
            <dd>{ETAPAS_LOGISTICAS[detalle.logistics.stage]}</dd>
          </div>
        ) : null}
      </dl>

      {detalle.allowed_actions.confirm_dispatch && (
        <div className="mt-6">
          <Autorizado
            operacion={[
              "POST",
              `/importaciones/${detalle.id}/confirm-dispatch`,
            ]}
          >
            <AsyncButton onClick={confirmarDespacho}>
              Confirmar despacho
            </AsyncButton>
          </Autorizado>
          {error && (
            <div
              role="alert"
              className="mt-3 rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600"
            >
              {error}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
