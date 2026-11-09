import { Link } from "react-router";

import { ReporteDiferenciasRecepcion } from "./ReporteDiferencias";
import { ESTADOS_INCIDENCIA, TIPOS_INCIDENCIA, type DetalleImportacion } from "./tipos";

type Props = {
  detalle: DetalleImportacion;
};

export function ImportacionDiferencias({ detalle }: Props): React.JSX.Element {
  const logistics = detalle.logistics;
  const incidencias = logistics?.incidents ?? [];
  const cantidades = logistics?.quantities ?? [];

  function cantidadFormateada(valor: number | null | undefined): string {
    return valor == null ? "—" : String(valor);
  }

  return (
    <section id="diferencias" className="rounded-lg border border-border-default bg-surface-0 p-6">
      <h2 className="mb-4 text-lg font-semibold text-text-900">Diferencias e inventario</h2>

      <h3 className="mb-2 text-md font-medium text-text-800">Incidencias</h3>
      {incidencias.length === 0 ? (
        <p className="mb-6 text-sm text-text-600">Sin incidencias registradas.</p>
      ) : (
        <ul className="mb-6 space-y-3">
          {incidencias.map((incidencia) => (
            <li key={incidencia.id} className="rounded-md border border-border-default bg-surface-0 p-4">
              <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
                <div>
                  <span className="text-text-600">Código:</span> {incidencia.code}
                </div>
                <div>
                  <span className="text-text-600">Recepción:</span> {incidencia.receipt_code}
                </div>
                <div>
                  <span className="text-text-600">Tipo:</span>{" "}
                  {TIPOS_INCIDENCIA[incidencia.incident_type] ?? incidencia.incident_type}
                </div>
                <div>
                  <span className="text-text-600">Producto:</span>{" "}
                  {incidencia.product_name ?? "Sin producto"}
                </div>
                <div>
                  <span className="text-text-600">Cantidad:</span>{" "}
                  {cantidadFormateada(incidencia.affected_base_quantity)}
                </div>
                <div>
                  <span className="text-text-600">Estado:</span>{" "}
                  {ESTADOS_INCIDENCIA[incidencia.status] ?? incidencia.status}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      <h3 className="mb-2 text-md font-medium text-text-800">Inventario por recepción</h3>
      {cantidades.length === 0 ? (
        <p className="mb-6 text-sm text-text-600">Sin cantidades registradas.</p>
      ) : (
        <div className="mb-6 overflow-x-auto">
          <table className="min-w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border-default text-left">
                <th className="py-2 pr-4 font-medium text-text-700">Recepción</th>
                <th className="py-2 pr-4 font-medium text-text-700">Producto</th>
                <th className="py-2 pr-4 font-medium text-text-700">Recibido</th>
                <th className="py-2 pr-4 font-medium text-text-700">Confirmado</th>
                <th className="py-2 pr-4 font-medium text-text-700">Rechazado</th>
              </tr>
            </thead>
            <tbody>
              {cantidades.map((cantidad) => (
                <tr key={`${cantidad.receipt_code}-${cantidad.product_id}`} className="border-b border-border-subtle">
                  <td className="py-2 pr-4">{cantidad.receipt_code}</td>
                  <td className="py-2 pr-4">{cantidad.product_name}</td>
                  <td className="py-2 pr-4">{cantidadFormateada(cantidad.received_base)}</td>
                  <td className="py-2 pr-4">{cantidadFormateada(cantidad.confirmed_available)}</td>
                  <td className="py-2 pr-4">{cantidadFormateada(cantidad.rejected)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="space-y-3">
        {(logistics?.receipts ?? [])
          .filter((recepcion) => recepcion.status !== "CANCELLED")
          .map((recepcion) => (
            <div key={recepcion.id} className="rounded-lg border border-border-default bg-surface-0 p-6">
              <div className="flex flex-wrap gap-3">
                <Link
                  to={`/compras/incidencias?recepcion=${recepcion.id}&importacion=${detalle.id}`}
                  className="text-sm font-medium text-brand-600 hover:text-brand-700"
                >
                  Gestionar incidencias de {recepcion.code}
                </Link>
                {["ACCEPTED", "PARTIALLY_ACCEPTED", "CLOSED"].includes(recepcion.status) &&
                recepcion.confirmation_status !== "CONFIRMADA" ? (
                  <Link
                    to={`/inventario/confirmacion?recepcion=${recepcion.id}&importacion=${detalle.id}`}
                    className="text-sm font-medium text-brand-600 hover:text-brand-700"
                  >
                    Confirmar inventario de {recepcion.code}
                  </Link>
                ) : null}
              </div>
              <ReporteDiferenciasRecepcion
                importacionId={detalle.id}
                recepcionId={recepcion.id}
                recepcionCodigo={recepcion.code}
              />
            </div>
          ))}
      </div>
    </section>
  );
}
