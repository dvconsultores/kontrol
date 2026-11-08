import { useState } from "react";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { Autorizado } from "@/components/Autorizado";
import { apiFetch } from "@/api/client";
import { AdjuntosPanel } from "@/modules/documentos/AdjuntosPanel";
import type { DetalleImportacion } from "./ImportacionDetallePage";

type Props = {
  detalle: DetalleImportacion;
  onCambios: () => void;
};

const RESPONSABLES = [
  { value: "PROVEEDOR", label: "Proveedor" },
  { value: "AGENTE", label: "Agente" },
  { value: "IMPORTACION", label: "Responsable de importación" },
];

const ESTADOS_FORMULARIO = new Set([
  "ORDERED",
  "DOCUMENTS_COMPLETE",
  "DISPATCHED",
]);

const ESTADOS_CORRECCION: Record<string, string> = {
  OPEN: "Abierta",
  RESOLVED: "Resuelta",
  CANCELLED: "Anulada",
};

export function ImportacionCorrecciones({ detalle, onCambios }: Props) {
  const [tipoCorreccion, setTipoCorreccion] = useState<
    "FALTANTE" | "CORRECCION_DOCUMENTAL"
  >("FALTANTE");
  const [descripcion, setDescripcion] = useState("");
  const [accionRequerida, setAccionRequerida] = useState("");
  const [responsable, setResponsable] = useState<
    "PROVEEDOR" | "AGENTE" | "IMPORTACION"
  >("PROVEEDOR");
  const [documentoId, setDocumentoId] = useState("");
  const [resoluciones, setResoluciones] = useState<Record<string, string>>({});
  const [motivosCancelacion, setMotivosCancelacion] = useState<
    Record<string, string>
  >({});
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  const esNegociando = detalle.status === "NEGOTIATING";
  const esCancelada = detalle.status === "CANCELLED";
  const mostrarFormulario = ESTADOS_FORMULARIO.has(detalle.status);

  const crearCorreccion = async () => {
    if (!descripcion.trim() || !accionRequerida.trim()) return;
    setGuardando(true);
    setError(null);
    try {
      await apiFetch(`/importaciones/${detalle.id}/corrections`, {
        method: "POST",
        body: {
          kind: tipoCorreccion,
          description: descripcion.trim(),
          action_required: accionRequerida.trim(),
          responsible: responsable,
          document_id: documentoId || null,
        },
      });
      setDescripcion("");
      setAccionRequerida("");
      setDocumentoId("");
      onCambios();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al crear corrección.");
    } finally {
      setGuardando(false);
    }
  };

  const resolverCorreccion = async (correccionId: string) => {
    const resolucion = resoluciones[correccionId]?.trim();
    if (!resolucion) return;
    setError(null);
    try {
      await apiFetch(
        `/importaciones/${detalle.id}/corrections/${correccionId}/resolve`,
        {
          method: "POST",
          body: { resolution: resolucion },
        },
      );
      setResoluciones((prev) => {
        const siguiente = { ...prev };
        delete siguiente[correccionId];
        return siguiente;
      });
      onCambios();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al resolver corrección.");
    }
  };

  const cancelarCorreccion = async (correccionId: string) => {
    const motivo = motivosCancelacion[correccionId]?.trim();
    if (!motivo) return;
    setError(null);
    try {
      await apiFetch(
        `/importaciones/${detalle.id}/corrections/${correccionId}/cancel`,
        {
          method: "POST",
          body: { reason: motivo },
        },
      );
      setMotivosCancelacion((prev) => {
        const siguiente = { ...prev };
        delete siguiente[correccionId];
        return siguiente;
      });
      onCambios();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cancelar corrección.");
    }
  };

  return (
    <section
      id="correcciones"
      className="rounded-lg border border-border-default bg-surface-0 p-6"
    >
      <h2 className="mb-4 text-lg font-semibold text-text-900">Correcciones</h2>

      {esNegociando && (
        <p className="mb-4 text-sm text-text-600">
          Se habilita al vincular la orden de compra.
        </p>
      )}

      {esCancelada ? null : (
        <>
          <div className="space-y-2">
            {detalle.corrections.length === 0 ? (
              <p className="text-sm text-text-600">Sin correcciones registradas.</p>
            ) : (
              <ul className="space-y-4">
                {detalle.corrections.map((correccion) => (
                  <li key={correccion.id} className="text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium">
                        {correccion.kind === "FALTANTE"
                          ? "Faltante"
                          : "Corrección documental"}
                      </span>
                      <span>
                        {ESTADOS_CORRECCION[correccion.status] ??
                          correccion.status}
                      </span>
                    </div>
                    <p className="mt-1">Descripción: {correccion.description}</p>
                    {correccion.action_required && (
                      <p className="mt-1">Acción requerida: {correccion.action_required}</p>
                    )}
                    {correccion.responsible_name && (
                      <p className="mt-1">Responsable: {correccion.responsible_name}</p>
                    )}
                    {correccion.resolution && (
                      <p className="mt-1">Resolución: {correccion.resolution}</p>
                    )}
                    {correccion.resolved_at && (
                      <p className="mt-1">
                        Resuelta el {correccion.resolved_at}
                      </p>
                    )}

                    {correccion.allowed_actions.resolve && (
                      <div className="mt-2 space-y-2">
                        <FormField label="Resolución" className="max-w-md">
                          <TextInput
                            value={resoluciones[correccion.id] ?? ""}
                            onChange={(e) =>
                              setResoluciones((prev) => ({
                                ...prev,
                                [correccion.id]: e.target.value,
                              }))
                            }
                          />
                        </FormField>
                        <Autorizado
                          operacion={[
                            "POST",
                            `/importaciones/${detalle.id}/corrections/${correccion.id}/resolve`,
                          ]}
                        >
                          <AsyncButton
                            disabled={
                              !(resoluciones[correccion.id] ?? "").trim()
                            }
                            onClick={() => resolverCorreccion(correccion.id)}
                          >
                            Resolver
                          </AsyncButton>
                        </Autorizado>
                      </div>
                    )}
                    {correccion.allowed_actions.cancel && (
                      <div className="mt-2 space-y-2">
                        <FormField
                          label="Motivo de anulación"
                          className="max-w-md"
                        >
                          <TextInput
                            value={motivosCancelacion[correccion.id] ?? ""}
                            onChange={(e) =>
                              setMotivosCancelacion((prev) => ({
                                ...prev,
                                [correccion.id]: e.target.value,
                              }))
                            }
                          />
                        </FormField>
                        <Autorizado
                          operacion={[
                            "POST",
                            `/importaciones/${detalle.id}/corrections/${correccion.id}/cancel`,
                          ]}
                        >
                          <AsyncButton
                            disabled={
                              !(motivosCancelacion[correccion.id] ?? "").trim()
                            }
                            onClick={() => cancelarCorreccion(correccion.id)}
                          >
                            Anular
                          </AsyncButton>
                        </Autorizado>
                      </div>
                    )}

                    <div className="mt-3">
                      <AdjuntosPanel
                        resourceType="ImportCorrection"
                        resourceId={correccion.id}
                        title="Evidencia de la corrección"
                        onChange={onCambios}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {mostrarFormulario && (
            <div className="mt-6 space-y-4">
              <FormField label="Tipo de corrección">
                <select
                  className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                  value={tipoCorreccion}
                  onChange={(e) =>
                    setTipoCorreccion(
                      e.target.value as "FALTANTE" | "CORRECCION_DOCUMENTAL",
                    )
                  }
                >
                  <option value="FALTANTE">Faltante</option>
                  <option value="CORRECCION_DOCUMENTAL">
                    Corrección documental
                  </option>
                </select>
              </FormField>
              <FormField label="Documento relacionado">
                <select
                  className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                  value={documentoId}
                  onChange={(e) => setDocumentoId(e.target.value)}
                >
                  <option value="">Sin documento</option>
                  {detalle.documents.map((documento) => (
                    <option key={documento.id} value={documento.id}>
                      {documento.name}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField label="Descripción" required>
                <TextInput
                  value={descripcion}
                  onChange={(e) => setDescripcion(e.target.value)}
                />
              </FormField>
              <FormField label="Acción requerida" required>
                <TextInput
                  value={accionRequerida}
                  onChange={(e) => setAccionRequerida(e.target.value)}
                />
              </FormField>
              <FormField label="Responsable">
                <select
                  className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                  value={responsable}
                  onChange={(e) =>
                    setResponsable(
                      e.target.value as "PROVEEDOR" | "AGENTE" | "IMPORTACION",
                    )
                  }
                >
                  {RESPONSABLES.map((responsable) => (
                    <option key={responsable.value} value={responsable.value}>
                      {responsable.label}
                    </option>
                  ))}
                </select>
              </FormField>

              <Autorizado
                operacion={["POST", `/importaciones/${detalle.id}/corrections`]}
              >
                <AsyncButton
                  disabled={
                    !descripcion.trim() ||
                    !accionRequerida.trim() ||
                    guardando
                  }
                  onClick={crearCorreccion}
                >
                  Crear corrección
                </AsyncButton>
              </Autorizado>
            </div>
          )}
        </>
      )}

      {error && (
        <div
          role="alert"
          className="mt-4 rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600"
        >
          {error}
        </div>
      )}
    </section>
  );
}
