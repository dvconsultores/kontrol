import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ApiError, apiFetch } from "@/api/client";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { Autorizado } from "@/components/Autorizado";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { formatearInstante } from "@/lib/fecha-de-negocio";
import type {
  FilaUbicacionFisica,
  UbicacionFisicaRespuesta,
  ValidacionUbicacion,
} from "./tipos";

type Props = {
  importacionId: string;
  onCambios: () => void;
};

function FilaFisica({
  fila,
  ubicaciones,
  importacionId,
  onCambios,
  onRefetch,
}: {
  fila: FilaUbicacionFisica;
  ubicaciones: Array<{ id: string; code: string; name: string | null; path: string }>;
  importacionId: string;
  onCambios: () => void;
  onRefetch: () => Promise<void>;
}): React.JSX.Element {
  const { notify } = useNotifications();
  const [ubicacionEncontrada, setUbicacionEncontrada] = useState("");
  const [cantidad, setCantidad] = useState(fila.quantity);
  const [dialogoAbierto, setDialogoAbierto] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [errorMotivo, setErrorMotivo] = useState(false);

  const v = fila.last_validation;

  const puedeReubicar =
    v !== null &&
    v.result === "MISMATCH" &&
    v.status === "PENDING" &&
    !v.stale;

  async function validar() {
    if (!ubicacionEncontrada) return;
    try {
      const respuesta = await apiFetch<ValidacionUbicacion>(
        `/importaciones/${importacionId}/physical-locations/validate`,
        {
          method: "POST",
          body: {
            receipt_id: fila.receipt_id,
            product_id: fila.product_id,
            state: fila.state,
            registered_location_id: fila.location.id,
            observed_location_id: ubicacionEncontrada,
            quantity: cantidad,
          },
        },
      );
      if (respuesta.result === "MATCH") {
        notify({ type: "success", title: "Ubicación física validada" });
      } else {
        notify({
          type: "warning",
          title: "La ubicación física no coincide con la registrada",
        });
      }
      await onRefetch();
      onCambios();
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.code === "LOCATION_VALIDATION_STALE") {
          notify({
            type: "warning",
            title: "La existencia cambió después de la validación. Valide de nuevo.",
          });
          await onRefetch();
          return;
        }
        notify({ type: "error", title: error.message });
        return;
      }
      notify({ type: "error", title: "No fue posible completar la operación." });
    }
  }

  async function confirmarReubicacion() {
    const motivoLimpio = motivo.trim();
    if (!motivoLimpio) {
      setErrorMotivo(true);
      return;
    }
    setErrorMotivo(false);
    if (!v) return;
    try {
      const respuesta = await apiFetch<ValidacionUbicacion>(
        `/inventory/location-validations/${v.id}/relocate`,
        {
          method: "POST",
          body: { quantity: v.quantity, reason: motivoLimpio },
        },
      );
      setDialogoAbierto(false);
      notify({
        type: "success",
        title: "Reubicación realizada",
        description: `Nueva ubicación registrada: ${respuesta.observed_location.code}`,
      });
      await onRefetch();
      onCambios();
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.code === "LOCATION_VALIDATION_STALE") {
          setDialogoAbierto(false);
          notify({
            type: "warning",
            title: "La existencia cambió después de la validación. Valide de nuevo.",
          });
          await onRefetch();
          return;
        }
        notify({ type: "error", title: error.message });
        return;
      }
      notify({ type: "error", title: "No fue posible completar la operación." });
    }
  }

  function estadoValidacion() {
    if (!v) return <p role="status">Sin validar</p>;
    if (v.status === "SUPERSEDED") return <p role="status">Sin validar</p>;
    if (v.result === "MATCH") {
      return <p role="status">Coincide · Ubicación física validada</p>;
    }
    if (v.result === "MISMATCH" && v.status === "PENDING" && !v.stale) {
      return (
        <div role="status">
          <p>No coincide</p>
          <p>Registrada: {v.registered_location.code}</p>
          <p>Encontrada: {v.observed_location.code}</p>
        </div>
      );
    }
    if (v.status === "PENDING" && v.stale) {
      return (
        <p role="status">
          La existencia cambió después de la validación: valide de nuevo
        </p>
      );
    }
    return <p role="status">Sin validar</p>;
  }

  return (
    <div
      role="group"
      aria-label={`${fila.product_name ?? "Producto"} en ${fila.location.code}`}
      className="rounded-md border border-border-subtle p-3"
    >
      <div className="mb-2 text-sm">
        <span className="font-medium">{fila.product_name}</span> · Recepción{" "}
        {fila.receipt_code} · Estado {fila.state} · Cantidad {fila.quantity}
      </div>
      <div className="mb-2 text-sm">
        <p>
          Ubicación registrada: {fila.location.code}
        </p>
        <p className="text-text-600">{fila.location.path}</p>
      </div>
      <div className="mb-3 text-sm">{estadoValidacion()}</div>

      <div className="grid grid-cols-2 gap-3">
        <Autorizado
          operacion={[
            "POST",
            `/importaciones/${importacionId}/physical-locations/validate`,
          ]}
        >
          <FormField label="Ubicación encontrada">
            <select
              className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
              value={ubicacionEncontrada}
              onChange={(e) => setUbicacionEncontrada(e.target.value)}
            >
              <option value="" disabled>
                Selecciona la ubicación encontrada
              </option>
              {ubicaciones.map((opcion) => (
                <option key={opcion.id} value={opcion.id}>
                  {opcion.code} · {opcion.path}
                </option>
              ))}
            </select>
          </FormField>
        </Autorizado>
        <Autorizado
          operacion={[
            "POST",
            `/importaciones/${importacionId}/physical-locations/validate`,
          ]}
        >
          <FormField label="Cantidad">
            <TextInput
              value={cantidad}
              onChange={(e) => setCantidad(e.target.value)}
            />
          </FormField>
        </Autorizado>
      </div>

      <div className="mt-3 flex flex-wrap gap-3">
        <Autorizado
          operacion={[
            "POST",
            `/importaciones/${importacionId}/physical-locations/validate`,
          ]}
        >
          <AsyncButton
            type="button"
            disabled={!ubicacionEncontrada}
            onClick={validar}
          >
            Validar ubicación física
          </AsyncButton>
        </Autorizado>

        {puedeReubicar && v ? (
          <Autorizado
            operacion={[
              "POST",
              `/inventory/location-validations/${v.id}/relocate`,
            ]}
          >
            <Button
              type="button"
              variant="secondary"
              onClick={() => setDialogoAbierto(true)}
            >
              Reubicar por error
            </Button>
          </Autorizado>
        ) : null}
      </div>

      {puedeReubicar && v ? (
        <ConfirmationDialog
          open={dialogoAbierto}
          title="Reubicar por error"
          confirmLabel="Confirmar reubicación"
          danger
          onConfirm={confirmarReubicacion}
          onCancel={() => {
            setDialogoAbierto(false);
            setErrorMotivo(false);
          }}
        >
          <dl>
            <div>
              <dt>Origen</dt>
              <dd>{v.registered_location.code}</dd>
            </div>
            <div>
              <dt>Destino</dt>
              <dd>{v.observed_location.code}</dd>
            </div>
            <div>
              <dt>Producto</dt>
              <dd>{v.product_name}</dd>
            </div>
            <div>
              <dt>Cantidad</dt>
              <dd>{v.quantity}</dd>
            </div>
            <div>
              <dt>Estado</dt>
              <dd>{v.state}</dd>
            </div>
          </dl>
          <FormField label="Motivo" required>
            <TextInput value={motivo} onChange={(e) => setMotivo(e.target.value)} />
          </FormField>
          {errorMotivo ? (
            <p role="alert">Escribe el motivo de la reubicación.</p>
          ) : null}
        </ConfirmationDialog>
      ) : null}
    </div>
  );
}

export function UbicacionFisica({ importacionId, onCambios }: Props): React.JSX.Element {
  const query = useQuery({
    queryKey: ["importaciones", importacionId, "ubicacion-fisica"],
    queryFn: () =>
      apiFetch<UbicacionFisicaRespuesta>(
        `/importaciones/${importacionId}/physical-locations`,
      ),
    refetchOnMount: "always",
  });

  if (query.isLoading) {
    return (
      <section
        aria-labelledby="ubicacion-fisica-titulo"
        className="mb-6 rounded-md border border-border-default p-4"
      >
        <h3
          id="ubicacion-fisica-titulo"
          className="mb-3 text-md font-medium text-text-800"
        >
          Ubicación física
        </h3>
        <p>Cargando ubicación física…</p>
      </section>
    );
  }

  if (query.isError || !query.data) {
    return (
      <section
        aria-labelledby="ubicacion-fisica-titulo"
        className="mb-6 rounded-md border border-border-default p-4"
      >
        <h3
          id="ubicacion-fisica-titulo"
          className="mb-3 text-md font-medium text-text-800"
        >
          Ubicación física
        </h3>
        <div role="alert">No fue posible cargar la ubicación física.</div>
      </section>
    );
  }

  const data = query.data;

  return (
    <section
      aria-labelledby="ubicacion-fisica-titulo"
      className="mb-6 rounded-md border border-border-default p-4"
    >
      <h3
        id="ubicacion-fisica-titulo"
        className="mb-3 text-md font-medium text-text-800"
      >
        Ubicación física
      </h3>

      {data.rows.length === 0 ? (
        <p>Sin mercancía ubicada para validar.</p>
      ) : (
        <div className="space-y-3">
          {data.rows.map((fila) => (
            <FilaFisica
              key={`${fila.receipt_id}-${fila.product_id}`}
              fila={fila}
              ubicaciones={data.locations_by_warehouse[fila.warehouse_id] ?? []}
              importacionId={importacionId}
              onCambios={onCambios}
              onRefetch={async () => {
                await query.refetch();
              }}
            />
          ))}
        </div>
      )}

      {data.history.length > 0 ? (
        <div className="mt-6">
          <h4>Historial de ubicación física</h4>
          <ul aria-label="Historial de ubicación física" className="space-y-2">
            {data.history.map((validacion) => {
              const resultado =
                validacion.status === "SUPERSEDED"
                  ? "Sustituida"
                  : validacion.result === "MATCH"
                    ? "Coincide"
                    : "No coincide";
              return (
                <li key={validacion.id}>
                  <span>
                    {formatearInstante(validacion.validated_at)} ·{" "}
                    {validacion.validated_by_name ?? "—"} ·{" "}
                    {validacion.registered_location.code} →{" "}
                    {validacion.observed_location.code} · {resultado}
                  </span>
                  {validacion.relocation ? (
                    <div>
                      Reubicado {validacion.relocation.quantity}:{" "}
                      {validacion.relocation.source_location.code} →{" "}
                      {validacion.relocation.target_location.code} · Motivo:{" "}
                      {validacion.relocation.reason} ·{" "}
                      {validacion.relocation.relocated_by_name ?? "—"}
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
