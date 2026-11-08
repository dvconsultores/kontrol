import { useState } from "react";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { Autorizado } from "@/components/Autorizado";
import { apiFetch, ApiError } from "@/api/client";
import { SelectorDeTercero } from "@/modules/maestros/terceros/SelectorDeTercero";
import type { DetalleImportacion } from "./ImportacionDetallePage";

type Props = {
  detalle: DetalleImportacion;
  onCambios: () => void;
};

const MILESTONES = [
  { value: "BOOKED", label: "Reservado" },
  { value: "DEPARTED", label: "Salida" },
  { value: "IN_TRANSIT", label: "En tránsito" },
  { value: "TRANSSHIPMENT", label: "Transbordo" },
  { value: "DELAYED", label: "Retraso" },
  { value: "OTHER", label: "Otro" },
];

const ESTADOS_FORMULARIO = new Set([
  "ORDERED",
  "DOCUMENTS_COMPLETE",
  "DISPATCHED",
]);

type FormEmbarque = {
  agente: string;
  transportista: string;
  documentoTransporte: string;
  origen: string;
  destino: string;
  salidaReal: string;
};

type FormHito = {
  milestone: string;
  occurred_on: string;
  location: string;
  notes: string;
};

export function ImportacionSeguimiento({ detalle, onCambios }: Props) {
  const [form, setForm] = useState<FormEmbarque>({
    agente: detalle.agent_party_id ?? "",
    transportista: detalle.carrier_party_id ?? "",
    documentoTransporte: detalle.transport_document ?? "",
    origen: detalle.origin ?? "",
    destino: detalle.destination ?? "",
    salidaReal: detalle.actual_departure_date ?? "",
  });
  const [hito, setHito] = useState<FormHito>({
    milestone: "BOOKED",
    occurred_on: "",
    location: "",
    notes: "",
  });
  const [errorSeguimiento, setErrorSeguimiento] = useState<string | null>(null);
  const [errorHito, setErrorHito] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [guardandoHito, setGuardandoHito] = useState(false);
  const [reload, setReload] = useState(false);

  const esNegociando = detalle.status === "NEGOTIATING";
  const esCancelada = detalle.status === "CANCELLED";
  const mostrarFormulario = ESTADOS_FORMULARIO.has(detalle.status);

  const guardarSeguimiento = async () => {
    setGuardando(true);
    setErrorSeguimiento(null);
    setReload(false);
    try {
      const body: Record<string, string | null> = {};
      if (form.agente !== (detalle.agent_party_id ?? "")) {
        body.agent_party_id = form.agente || null;
      }
      if (form.transportista !== (detalle.carrier_party_id ?? "")) {
        body.carrier_party_id = form.transportista || null;
      }
      if (form.documentoTransporte !== (detalle.transport_document ?? "")) {
        body.transport_document = form.documentoTransporte || null;
      }
      if (form.origen !== (detalle.origin ?? "")) {
        body.origin = form.origen || null;
      }
      if (form.destino !== (detalle.destination ?? "")) {
        body.destination = form.destino || null;
      }
      if (form.salidaReal !== (detalle.actual_departure_date ?? "")) {
        body.actual_departure_date = form.salidaReal || null;
      }

      await apiFetch(`/importaciones/${detalle.id}`, {
        method: "PATCH",
        body,
        ifMatch: String(detalle.version),
      });
      onCambios();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setErrorSeguimiento("El expediente cambió. Recarga para continuar.");
        setReload(true);
      } else {
        setErrorSeguimiento(
          err instanceof Error ? err.message : "Error al guardar seguimiento.",
        );
      }
    } finally {
      setGuardando(false);
    }
  };

  const registrarHito = async () => {
    setGuardandoHito(true);
    setErrorHito(null);
    try {
      await apiFetch(`/importaciones/${detalle.id}/tracking`, {
        method: "POST",
        body: {
          milestone: hito.milestone,
          occurred_on: hito.occurred_on,
          location: hito.location || null,
          notes: hito.notes || null,
        },
      });
      setHito({
        milestone: "BOOKED",
        occurred_on: "",
        location: "",
        notes: "",
      });
      onCambios();
    } catch (err) {
      setErrorHito(
        err instanceof Error ? err.message : "Error al registrar hito.",
      );
    } finally {
      setGuardandoHito(false);
    }
  };

  return (
    <section
      id="seguimiento"
      className="rounded-lg border border-border-default bg-surface-0 p-6"
    >
      <h2 className="mb-4 text-lg font-semibold text-text-900">Seguimiento</h2>

      {esNegociando && (
        <p className="mb-4 text-sm text-text-600">
          Se habilita al vincular la orden de compra.
        </p>
      )}

      {esCancelada ? null : (
        <>
          {detalle.tracking_events.length === 0 ? (
            <p className="text-sm text-text-600">Sin hitos registrados.</p>
          ) : (
            <ul className="space-y-2">
              {detalle.tracking_events.map((hito) => (
                <li key={hito.id} className="text-sm">
                  <span className="font-medium">
                    {MILESTONES.find((m) => m.value === hito.milestone)?.label ??
                      hito.milestone}
                  </span>{" "}
                  <span>{hito.occurred_on}</span>
                  {hito.location && <span> · {hito.location}</span>}
                  {hito.notes && <span> · {hito.notes}</span>}
                  {hito.username && <span> · {hito.username}</span>}
                </li>
              ))}
            </ul>
          )}

          {mostrarFormulario && (
            <div className="mt-6 space-y-4">
              <FormField label="Agente">
                <SelectorDeTercero
                  soloActivos
                  value={form.agente}
                  onChange={(id) =>
                    setForm((prev) => ({ ...prev, agente: id }))
                  }
                />
              </FormField>
              <FormField label="Transportista">
                <SelectorDeTercero
                  role="TRANSPORTISTA"
                  soloActivos
                  value={form.transportista}
                  onChange={(id) =>
                    setForm((prev) => ({ ...prev, transportista: id }))
                  }
                />
              </FormField>
              <FormField label="Documento de transporte">
                <TextInput
                  value={form.documentoTransporte}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      documentoTransporte: e.target.value,
                    }))
                  }
                />
              </FormField>
              <FormField label="Origen">
                <TextInput
                  value={form.origen}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, origen: e.target.value }))
                  }
                />
              </FormField>
              <FormField label="Destino">
                <TextInput
                  value={form.destino}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, destino: e.target.value }))
                  }
                />
              </FormField>
              <FormField label="Salida real">
                <TextInput
                  type="date"
                  value={form.salidaReal}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      salidaReal: e.target.value,
                    }))
                  }
                />
              </FormField>

              {errorSeguimiento && (
                <div
                  role="alert"
                  className="rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600"
                >
                  {errorSeguimiento}
                </div>
              )}

              {reload && (
                <button
                  type="button"
                  className="text-sm font-medium text-brand-600 hover:text-brand-700"
                  onClick={onCambios}
                >
                  Recargar
                </button>
              )}

              <Autorizado
                operacion={["PATCH", `/importaciones/${detalle.id}`]}
              >
                <AsyncButton
                  disabled={guardando}
                  onClick={guardarSeguimiento}
                >
                  Guardar seguimiento
                </AsyncButton>
              </Autorizado>

              <div className="mt-8 border-t border-border-default pt-6">
                <h3 className="mb-4 text-base font-medium text-text-800">
                  Registrar hito
                </h3>
                <div className="space-y-4">
                  <FormField label="Hito">
                    <select
                      value={hito.milestone}
                      onChange={(e) =>
                        setHito((prev) => ({
                          ...prev,
                          milestone: e.target.value,
                        }))
                      }
                      className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
                    >
                      <option value="">Seleccione un hito</option>
                      {MILESTONES.map((m) => (
                        <option key={m.value} value={m.value}>
                          {m.label}
                        </option>
                      ))}
                    </select>
                  </FormField>
                  <FormField label="Fecha" required>
                    <TextInput
                      type="date"
                      value={hito.occurred_on}
                      onChange={(e) =>
                        setHito((prev) => ({
                          ...prev,
                          occurred_on: e.target.value,
                        }))
                      }
                    />
                  </FormField>
                  <FormField label="Lugar">
                    <TextInput
                      value={hito.location}
                      onChange={(e) =>
                        setHito((prev) => ({
                          ...prev,
                          location: e.target.value,
                        }))
                      }
                    />
                  </FormField>
                  <FormField label="Notas">
                    <TextInput
                      value={hito.notes}
                      onChange={(e) =>
                        setHito((prev) => ({
                          ...prev,
                          notes: e.target.value,
                        }))
                      }
                    />
                  </FormField>

                  {errorHito && (
                    <div
                      role="alert"
                      className="rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600"
                    >
                      {errorHito}
                    </div>
                  )}

                  <Autorizado
                    operacion={["POST", `/importaciones/${detalle.id}/tracking`]}
                  >
                    <AsyncButton
                      disabled={guardandoHito || !hito.occurred_on}
                      onClick={registrarHito}
                    >
                      Registrar hito
                    </AsyncButton>
                  </Autorizado>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}
