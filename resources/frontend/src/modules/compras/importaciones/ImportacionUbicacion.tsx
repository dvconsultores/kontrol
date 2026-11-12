import { formatearInstante } from "@/lib/fecha-de-negocio";

import type { DetalleImportacion } from "./tipos";
import { UbicacionFisica } from "./UbicacionFisica";
import { ClasificacionAlmacenamiento } from "./ClasificacionAlmacenamiento";

type Props = {
  detalle: DetalleImportacion;
  onCambios: () => void;
};

export function ImportacionUbicacion({ detalle, onCambios }: Props): React.JSX.Element {
  const logistics = detalle.logistics;
  const cantidades = logistics?.quantities ?? [];
  const ubicaciones = logistics?.locations ?? [];
  const traza = logistics?.putaway_trace ?? [];

  return (
    <section id="ubicacion" className="rounded-lg border border-border-default bg-surface-0 p-6">
      <h2 className="mb-4 text-lg font-semibold text-text-900">Ubicación</h2>

      {cantidades.length > 0 ? (
        <div className="mb-6 overflow-x-auto">
          <table className="min-w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border-default text-left">
                <th className="py-2 pr-4 font-medium text-text-700">Recepción</th>
                <th className="py-2 pr-4 font-medium text-text-700">Producto</th>
                <th className="py-2 pr-4 font-medium text-text-700">Pendiente</th>
                <th className="py-2 pr-4 font-medium text-text-700">Ubicado</th>
              </tr>
            </thead>
            <tbody>
              {cantidades.map((cantidad) => (
                <tr key={`${cantidad.receipt_code}-${cantidad.product_id}`} className="border-b border-border-subtle">
                  <td className="py-2 pr-4">{cantidad.receipt_code}</td>
                  <td className="py-2 pr-4">{cantidad.product_name}</td>
                  <td className="py-2 pr-4">{cantidad.pending_putaway ?? "—"}</td>
                  <td className="py-2 pr-4">{cantidad.located ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {ubicaciones.length > 0 ? (
        <div className="mb-6 overflow-x-auto">
          <table className="min-w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border-default text-left">
                <th className="py-2 pr-4 font-medium text-text-700">Producto</th>
                <th className="py-2 pr-4 font-medium text-text-700">Ubicación</th>
                <th className="py-2 pr-4 font-medium text-text-700">Cantidad</th>
              </tr>
            </thead>
            <tbody>
              {ubicaciones.map((ubicacion, index) => (
                <tr key={`${ubicacion.product_name}-${ubicacion.location_label}-${index}`} className="border-b border-border-subtle">
                  <td className="py-2 pr-4">{ubicacion.product_name}</td>
                  <td className="py-2 pr-4">{ubicacion.location_label}</td>
                  <td className="py-2 pr-4">{ubicacion.quantity ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="mb-6 text-sm text-text-600">Sin mercancía ubicada.</p>
      )}

      <div role="region" aria-labelledby="traza-ubicacion-titulo" className="mb-6">
        <h3 id="traza-ubicacion-titulo" className="mb-2 text-base font-semibold text-text-900">
          Trazabilidad hasta la ubicación final
        </h3>
        {traza.length === 0 ? (
          <p className="text-sm text-text-600">Sin movimientos de ubicación.</p>
        ) : (
          <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Movimientos de ubicación de la importación">
            <table className="min-w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-border-default text-left">
                  <th className="py-2 pr-4 font-medium text-text-700">Recepción</th>
                  <th className="py-2 pr-4 font-medium text-text-700">Producto</th>
                  <th className="py-2 pr-4 font-medium text-text-700">Almacén</th>
                  <th className="py-2 pr-4 font-medium text-text-700">Desde</th>
                  <th className="py-2 pr-4 font-medium text-text-700">Hacia</th>
                  <th className="py-2 pr-4 font-medium text-text-700">Cantidad</th>
                  <th className="py-2 pr-4 font-medium text-text-700">Fecha</th>
                  <th className="py-2 pr-4 font-medium text-text-700">Usuario</th>
                </tr>
              </thead>
              <tbody>
                {traza.map((fila, index) => (
                  <tr
                    key={`${fila.occurred_at}-${index}`}
                    className="border-b border-border-subtle"
                  >
                    <td className="py-2 pr-4">{fila.receipt_code ?? "—"}</td>
                    <td className="py-2 pr-4">{fila.product_name ?? "—"}</td>
                    <td className="py-2 pr-4">{fila.warehouse_name ?? "—"}</td>
                    <td className="py-2 pr-4">
                      {fila.from_location_label === null ? "Sin ubicar" : fila.from_location_label}
                    </td>
                    <td className="py-2 pr-4">{fila.to_location_label ?? "—"}</td>
                    <td className="py-2 pr-4">{String(Number(fila.base_quantity))}</td>
                    <td className="py-2 pr-4">{formatearInstante(fila.occurred_at)}</td>
                    <td className="py-2 pr-4">{fila.actor_name ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <UbicacionFisica importacionId={detalle.id} onCambios={onCambios} />

      <ClasificacionAlmacenamiento importacionId={detalle.id} onCambios={onCambios} />
    </section>
  );
}
