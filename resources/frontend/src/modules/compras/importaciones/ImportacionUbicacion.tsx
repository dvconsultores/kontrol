import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import type { DetalleImportacion, PutawayPendiente } from "./tipos";
import { UbicacionFisica } from "./UbicacionFisica";

type Props = {
  detalle: DetalleImportacion;
  onCambios: () => void;
};

function FilaPutaway({
  pendiente,
  onCambios,
}: {
  pendiente: PutawayPendiente;
  onCambios: () => void;
}): React.JSX.Element {
  const [ubicacion, setUbicacion] = useState("");
  const [cantidad, setCantidad] = useState(pendiente.pending_base?.toString() ?? "");
  const [error, setError] = useState<string | null>(null);

  const ubicacionesQuery = useQuery({
    queryKey: ["importaciones", "ubicaciones", pendiente.warehouse_id],
    queryFn: async () => {
      const respuesta = await apiFetch<{ items: Array<{ code: string; name: string; id: string }> }>(
        `/inventory/putaway/ubicaciones?warehouse_id=${pendiente.warehouse_id}`,
      );
      return respuesta.items ?? [];
    },
    enabled: Boolean(pendiente.warehouse_id),
  });

  async function ubicar() {
    setError(null);
    if (!ubicacion) {
      setError("Elige una ubicación de destino");
      return;
    }
    try {
      await apiFetch("/inventory/putaway", {
        method: "POST",
        body: {
          product_id: pendiente.product_id,
          warehouse_id: pendiente.warehouse_id,
          target_location_id: ubicacion,
          quantity: cantidad,
          state: pendiente.state,
          lot_id: pendiente.lot_id,
          serial_id: pendiente.serial_id,
          document_ref: pendiente.receipt_code,
        },
      });
      onCambios();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo ubicar la mercancía");
    }
  }

  return (
    <div className="rounded-md border border-border-default bg-surface-0 p-4">
      <div className="mb-3 text-sm">
        <span className="font-medium">{pendiente.product_name}</span>{" "}
        <span className="text-text-600">· Pendiente: {pendiente.pending_base ?? "—"}</span>
      </div>
      {error ? (
        <div role="alert" className="mb-3 rounded-md border border-danger-200 bg-danger-50 p-3 text-sm text-danger-700">
          {error}
        </div>
      ) : null}
      <div className="grid grid-cols-2 gap-3">
        <FormField label="Ubicación de destino" required>
          <select
            className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
            value={ubicacion}
            onChange={(e) => setUbicacion(e.target.value)}
          >
            <option value="" disabled>
              Selecciona una ubicación
            </option>
            {(ubicacionesQuery.data ?? []).map((opcion) => (
              <option key={opcion.id} value={opcion.id}>
                {opcion.code} - {opcion.name}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Cantidad" required>
          <TextInput
            value={cantidad}
            onChange={(e) => setCantidad(e.target.value)}
          />
        </FormField>
      </div>
      <div className="mt-3">
        <Autorizado operacion={["POST", "/inventory/putaway"]}>
          <AsyncButton type="button" disabled={!ubicacion} onClick={ubicar}>
            Ubicar {pendiente.product_name}
          </AsyncButton>
        </Autorizado>
      </div>
    </div>
  );
}

export function ImportacionUbicacion({ detalle, onCambios }: Props): React.JSX.Element {
  const logistics = detalle.logistics;
  const cantidades = logistics?.quantities ?? [];
  const ubicaciones = logistics?.locations ?? [];
  const pendientes = logistics?.putaway_pending ?? [];

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

      {pendientes.length === 0 ? (
        <p className="text-sm text-text-600">Sin mercancía pendiente de ubicar.</p>
      ) : (
        <div className="space-y-3">
          {pendientes.map((pendiente) => (
            <FilaPutaway
              key={`${pendiente.receipt_code}-${pendiente.product_id}`}
              pendiente={pendiente}
              onCambios={onCambios}
            />
          ))}
        </div>
      )}
    </section>
  );
}
