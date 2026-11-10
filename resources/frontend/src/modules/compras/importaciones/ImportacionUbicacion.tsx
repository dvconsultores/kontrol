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

      <UbicacionFisica importacionId={detalle.id} onCambios={onCambios} />

      <ClasificacionAlmacenamiento importacionId={detalle.id} onCambios={onCambios} />
    </section>
  );
}
