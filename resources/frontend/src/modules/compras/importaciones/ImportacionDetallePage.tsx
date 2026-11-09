import { useState } from "react";
import { Link, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import type { PagedResult } from "@/api/types";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";
import { Button } from "@/components/Button";
import { AsyncButton } from "@/components/AsyncButton";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { TextInput } from "@/components/TextInput";
import { FormField } from "@/components/FormField";
import { Autorizado } from "@/components/Autorizado";
import { UnsavedChangesGuard } from "@/components/UnsavedChangesGuard";
import { AdjuntosPanel } from "@/modules/documentos/AdjuntosPanel";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { formatearInstante } from "@/lib/fecha-de-negocio";
import { AsyncCombobox } from "@/components/AsyncCombobox";
import { ImportacionResumen } from "./ImportacionResumen";
import { ImportacionSeguimiento } from "./ImportacionSeguimiento";
import { ImportacionFinanzas } from "./ImportacionFinanzas";
import { ImportacionCorrecciones } from "./ImportacionCorrecciones";
import { ImportacionDiferencias } from "./ImportacionDiferencias";
import { ImportacionRecepcion } from "./ImportacionRecepcion";
import { ImportacionUbicacion } from "./ImportacionUbicacion";
import { ImportacionCostos } from "./ImportacionCostos";
import {
  ESTADOS,
  ESTADOS_DOCUMENTO,
  INCOTERMS,
  importacionKey,
  type Documento,
  type DetalleImportacion,
} from "./tipos";


export type { DetalleImportacion } from "./tipos";

type EventoAuditoria = {
  id: string;
  action: string;
  action_label: string;
  event_time: string;
  username: string | null;
  reason: string | null;
  details: Record<string, unknown> | null;
};

type FormNegociacion = {
  incoterm: string;
  incoterm_place: string;
  payment_conditions: string;
  delivery_conditions: string;
  expected_dispatch_date: string;
  expected_arrival_date: string;
  notes: string;
};

function Negociacion({
  detalle,
  onCambios,
}: {
  detalle: DetalleImportacion;
  onCambios: () => void;
}) {
  const { notify } = useNotifications();
  const [error, setError] = useState<string | null>(null);
  const [conflicto, setConflicto] = useState(false);
  const [form, setForm] = useState<FormNegociacion>(() => ({
    incoterm: detalle.incoterm ?? "",
    incoterm_place: detalle.incoterm_place ?? "",
    payment_conditions: detalle.payment_conditions ?? "",
    delivery_conditions: detalle.delivery_conditions ?? "",
    expected_dispatch_date: detalle.expected_dispatch_date ?? "",
    expected_arrival_date: detalle.expected_arrival_date ?? "",
    notes: detalle.notes ?? "",
  }));

  const editable =
    detalle.status === "NEGOTIATING" || detalle.status === "ORDERED";
  const disabledClases =
    "disabled:cursor-not-allowed disabled:bg-surface-100 disabled:text-text-400";

  const dirty =
    form.incoterm !== (detalle.incoterm ?? "") ||
    form.incoterm_place !== (detalle.incoterm_place ?? "") ||
    form.payment_conditions !== (detalle.payment_conditions ?? "") ||
    form.delivery_conditions !== (detalle.delivery_conditions ?? "") ||
    form.expected_dispatch_date !== (detalle.expected_dispatch_date ?? "") ||
    form.expected_arrival_date !== (detalle.expected_arrival_date ?? "") ||
    form.notes !== (detalle.notes ?? "");

  const guardar = async () => {
    const body: Record<string, string | null> = {};
    if (form.incoterm !== (detalle.incoterm ?? "")) body.incoterm = form.incoterm || null;
    if (form.incoterm_place !== (detalle.incoterm_place ?? ""))
      body.incoterm_place = form.incoterm_place || null;
    if (form.payment_conditions !== (detalle.payment_conditions ?? ""))
      body.payment_conditions = form.payment_conditions || null;
    if (form.delivery_conditions !== (detalle.delivery_conditions ?? ""))
      body.delivery_conditions = form.delivery_conditions || null;
    if (form.expected_dispatch_date !== (detalle.expected_dispatch_date ?? ""))
      body.expected_dispatch_date = form.expected_dispatch_date || null;
    if (form.expected_arrival_date !== (detalle.expected_arrival_date ?? ""))
      body.expected_arrival_date = form.expected_arrival_date || null;
    if (form.notes !== (detalle.notes ?? "")) body.notes = form.notes || null;

    try {
      await apiFetch(`/importaciones/${detalle.id}`, {
        method: "PATCH",
        body,
        ifMatch: String(detalle.version),
      });
      setError(null);
      setConflicto(false);
      notify({ type: "success", title: "Negociación guardada." });
      onCambios();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setConflicto(true);
        setError("Otro usuario modificó esta importación. Recargue para ver los cambios.");
      } else {
        setError(err instanceof Error ? err.message : "Error al guardar.");
      }
    }
  };

  const setCampo = (campo: keyof FormNegociacion, valor: string) => {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  };

  return (
    <section
      id="negociacion"
      key={detalle.version}
      className="rounded-lg border border-border-default bg-surface-0 p-6"
    >
      <UnsavedChangesGuard hasUnsavedChanges={dirty && editable} />
      <h2 className="mb-4 text-lg font-semibold text-text-900">Negociación</h2>
      <div className="grid gap-4 md:grid-cols-2">
        <FormField label="INCOTERM">
          <select
            className={`h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 ${disabledClases}`}
            value={form.incoterm}
            disabled={!editable}
            onChange={(e) => setCampo("incoterm", e.target.value)}
          >
            <option value="">Sin definir</option>
            {INCOTERMS.map((incoterm) => (
              <option key={incoterm} value={incoterm}>
                {incoterm}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Lugar del INCOTERM">
          <TextInput
            value={form.incoterm_place}
            disabled={!editable}
            onChange={(e) => setCampo("incoterm_place", e.target.value)}
          />
        </FormField>
      </div>
      <FormField label="Condiciones de pago">
        <textarea
          className={`min-h-20 w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 ${disabledClases}`}
          value={form.payment_conditions}
          disabled={!editable}
          onChange={(e) => setCampo("payment_conditions", e.target.value)}
        />
      </FormField>
      <FormField label="Condiciones de entrega">
        <textarea
          className={`min-h-20 w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 ${disabledClases}`}
          value={form.delivery_conditions}
          disabled={!editable}
          onChange={(e) => setCampo("delivery_conditions", e.target.value)}
        />
      </FormField>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <FormField label="Despacho previsto">
          <TextInput
            type="date"
            value={form.expected_dispatch_date}
            disabled={!editable}
            onChange={(e) => setCampo("expected_dispatch_date", e.target.value)}
          />
        </FormField>
        <FormField label="Llegada prevista">
          <TextInput
            type="date"
            value={form.expected_arrival_date}
            disabled={!editable}
            onChange={(e) => setCampo("expected_arrival_date", e.target.value)}
          />
        </FormField>
      </div>
      <FormField label="Notas">
        <textarea
          className={`min-h-20 w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 ${disabledClases}`}
          value={form.notes}
          disabled={!editable}
          onChange={(e) => setCampo("notes", e.target.value)}
        />
      </FormField>
      {error && (
        <div role="alert" className="rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600">
          {error}
        </div>
      )}
      {conflicto && (
        <div className="mt-3">
          <Button
            variant="secondary"
            onClick={() => onCambios()}
          >
            Recargar
          </Button>
        </div>
      )}
      {editable && (
        <div className="mt-4">
          <Autorizado operacion={["PATCH", `/importaciones/${detalle.id}`]}>
            <AsyncButton disabled={!dirty} onClick={guardar}>
              Guardar negociación
            </AsyncButton>
          </Autorizado>
        </div>
      )}
    </section>
  );
}

function VincularOrden({
  detalle,
  onCambios,
}: {
  detalle: DetalleImportacion;
  onCambios: () => void;
}) {
  const { activeCompany } = useCompany();
  const [ordenId, setOrdenId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const vincular = async () => {
    if (!ordenId) return;
    try {
      await apiFetch(`/importaciones/${detalle.id}/order`, {
        method: "POST",
        body: { order_id: ordenId },
      });
      setError(null);
      onCambios();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409 && err.details?.missing) {
        const etiquetas: Record<string, string> = {
          incoterm: "INCOTERM",
          payment_conditions: "Condiciones de pago",
          delivery_conditions: "Condiciones de entrega",
        };
        const missing = Array.isArray(err.details.missing)
          ? err.details.missing.map((campo) => etiquetas[String(campo)] ?? String(campo))
          : [];
        setError(`Completa la negociación: ${missing.join(", ")}`);
      } else {
        setError(err instanceof Error ? err.message : "Error al vincular.");
      }
    }
  };

  return (
    <section
      id="orden"
      className="rounded-lg border border-border-default bg-surface-0 p-6"
    >
      <h2 className="mb-4 text-lg font-semibold text-text-900">Orden de compra</h2>
      {detalle.order_code ? (
        <div className="flex items-center gap-3">
          <span>Orden {detalle.order_code}</span>
          <Link to="/compras/ordenes">
            <Button variant="secondary" size="sm">
              Ver órdenes
            </Button>
          </Link>
        </div>
      ) : detalle.allowed_actions.link_order ? (
        <div className="space-y-3">
          <FormField label="Orden aprobada">
            <AsyncCombobox
              value={ordenId}
              onChange={(value) => setOrdenId(value)}
              searchUrl="/importaciones/eligible-orders"
              extraParams={{ file_id: detalle.id }}
              scopeKey={activeCompany?.id ?? ""}
              id="orden-aprobada"
              placeholder="Buscar orden aprobada…"
            />
          </FormField>
          <Autorizado operacion={["POST", `/importaciones/${detalle.id}/order`]}>
            <AsyncButton disabled={!ordenId} onClick={vincular}>
              Vincular orden
            </AsyncButton>
          </Autorizado>
        </div>
      ) : null}
      {error && (
        <div role="alert" className="rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600">
          {error}
        </div>
      )}
    </section>
  );
}

function Documentos({
  detalle,
  onCambios,
}: {
  detalle: DetalleImportacion;
  onCambios: () => void;
}) {
  const esCancelada = detalle.status === "CANCELLED";
  const [nombreCertificado, setNombreCertificado] = useState("");
  const [referencias, setReferencias] = useState<Record<string, string>>({});
  const [observaciones, setObservaciones] = useState<Record<string, string>>({});
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [errorConfirmar, setErrorConfirmar] = useState<string | null>(null);

  const setReferencia = (documentoId: string, valor: string) => {
    setReferencias((prev) => ({ ...prev, [documentoId]: valor }));
  };

  const setObservacion = (documentoId: string, valor: string) => {
    setObservaciones((prev) => ({ ...prev, [documentoId]: valor }));
  };

  const accionDocumento = async (
    documento: Documento,
    tipo: "receive" | "validate" | "observe",
  ) => {
    if (tipo === "receive" && !referencias[documento.id]?.trim()) {
      setErrores((prev) => ({ ...prev, [documento.id]: "Indica la referencia del documento." }));
      return;
    }
    if (tipo === "observe" && !observaciones[documento.id]?.trim()) {
      setErrores((prev) => ({ ...prev, [documento.id]: "Indica la observación." }));
      return;
    }

    try {
      const path = `/importaciones/${detalle.id}/documents/${documento.id}/${tipo}`;
      const body =
        tipo === "receive"
          ? { reference: referencias[documento.id] }
          : tipo === "observe"
            ? { observation: observaciones[documento.id] }
            : undefined;
      await apiFetch(path, { method: "POST", body });
      setErrorConfirmar(null);
      setErrores((prev) => {
        const siguiente = { ...prev };
        delete siguiente[documento.id];
        return siguiente;
      });
      onCambios();
    } catch (err) {
      setErrores((prev) => ({
        ...prev,
        [documento.id]: err instanceof Error ? err.message : "Error al actualizar documento.",
      }));
    }
  };

  const confirmarDocumentacion = async () => {
    try {
      await apiFetch(`/importaciones/${detalle.id}/confirm-documents`, {
        method: "POST",
      });
      setErrorConfirmar(null);
      onCambios();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409 && err.details?.missing) {
        const missing = Array.isArray(err.details.missing)
          ? err.details.missing.map((nombre) => String(nombre))
          : [];
        setErrorConfirmar(`Falta validar: ${missing.join(", ")}`);
      } else {
        setErrorConfirmar(err instanceof Error ? err.message : "Error al confirmar documentación.");
      }
    }
  };

  return (
    <section
      id="documentacion"
      className="rounded-lg border border-border-default bg-surface-0 p-6"
    >
      <h2 className="mb-4 text-lg font-semibold text-text-900">Documentos</h2>
      {esCancelada ? (
        <p className="text-sm text-text-600">
          La documentación no está disponible para una importación cancelada.
        </p>
      ) : (
      <>
      <div className="space-y-4">
        {detalle.documents.map((documento) => {
          const errorDocumento = errores[documento.id];
          return (
            <div key={documento.id} className="rounded-lg border border-border-default p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{documento.name}</span>
                {documento.required && <span>Obligatorio</span>}
                {documento.reference && <span>{documento.reference}</span>}
                <span>{ESTADOS_DOCUMENTO[documento.status]}</span>
              </div>
              {documento.observation && (
                <p className="mt-2 text-sm text-text-600">{documento.observation}</p>
              )}
              <div className="mt-3 flex flex-wrap items-end gap-2">
                {documento.allowed_actions.receive && (
                  <>
                    <FormField label={`Referencia de ${documento.name}`} className="min-w-64 flex-1">
                      <TextInput
                        value={referencias[documento.id] ?? ""}
                        onChange={(e) => setReferencia(documento.id, e.target.value)}
                      />
                    </FormField>
                    <Autorizado
                      operacion={[
                        "POST",
                        `/importaciones/${detalle.id}/documents/${documento.id}/receive`,
                      ]}
                    >
                      <AsyncButton onClick={() => accionDocumento(documento, "receive")}>
                        Recibir {documento.name}
                      </AsyncButton>
                    </Autorizado>
                  </>
                )}
                {documento.allowed_actions.validate && (
                  <Autorizado
                    operacion={[
                      "POST",
                      `/importaciones/${detalle.id}/documents/${documento.id}/validate`,
                    ]}
                  >
                    <AsyncButton onClick={() => accionDocumento(documento, "validate")}>
                      Validar {documento.name}
                    </AsyncButton>
                  </Autorizado>
                )}
                {documento.allowed_actions.observe && (
                  <>
                    <FormField label={`Observación de ${documento.name}`} className="min-w-64 flex-1">
                      <TextInput
                        value={observaciones[documento.id] ?? ""}
                        onChange={(e) => setObservacion(documento.id, e.target.value)}
                      />
                    </FormField>
                    <Autorizado
                      operacion={[
                        "POST",
                        `/importaciones/${detalle.id}/documents/${documento.id}/observe`,
                      ]}
                    >
                      <AsyncButton onClick={() => accionDocumento(documento, "observe")}>
                        Observar {documento.name}
                      </AsyncButton>
                    </Autorizado>
                  </>
                )}
              </div>
              {errorDocumento && (
                <div role="alert" className="mt-3 rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600">
                  {errorDocumento}
                </div>
              )}
              {documento.status !== "PENDING" && (
                <AdjuntosPanel
                  resourceType="ImportDocument"
                  resourceId={documento.id}
                  title={`Archivo de ${documento.name}`}
                  onChange={onCambios}
                />
              )}
            </div>
          );
        })}
      </div>
      {detalle.allowed_actions.add_document && (
        <div className="mt-4 flex flex-wrap items-end gap-2">
          <FormField label="Nombre del certificado o soporte" className="min-w-64 flex-1">
            <TextInput
              value={nombreCertificado}
              onChange={(e) => setNombreCertificado(e.target.value)}
            />
          </FormField>
          <Autorizado operacion={["POST", `/importaciones/${detalle.id}/documents`]}>
            <AsyncButton
              onClick={async () => {
                if (!nombreCertificado.trim()) return;
                try {
                  await apiFetch(`/importaciones/${detalle.id}/documents`, {
                    method: "POST",
                    body: { kind: "CERTIFICATE", name: nombreCertificado.trim() },
                  });
                  setNombreCertificado("");
                  onCambios();
                } catch (err) {
                  setErrorConfirmar(
                    err instanceof Error ? err.message : "Error al añadir documento.",
                  );
                }
              }}
            >
              Añadir certificado
            </AsyncButton>
          </Autorizado>
        </div>
      )}
      {detalle.allowed_actions.confirm_documents && (
        <div className="mt-4">
          <Autorizado operacion={["POST", `/importaciones/${detalle.id}/confirm-documents`]}>
            <AsyncButton onClick={confirmarDocumentacion}>
              Confirmar documentación
            </AsyncButton>
          </Autorizado>
        </div>
      )}
      {errorConfirmar && (
        <div role="alert" className="mt-3 rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600">
          {errorConfirmar}
        </div>
      )}
      </>
      )}
    </section>
  );
}

function Historial({ id }: { id: string }) {
  const { data } = useQuery({
    queryKey: ["importaciones", id, "audit"],
    queryFn: () =>
      apiFetch<PagedResult<EventoAuditoria>>(`/importaciones/${id}/audit?page=1&page_size=100`),
  });

  return (
    <section
      id="historial"
      className="rounded-lg border border-border-default bg-surface-0 p-6"
    >
      <h2 className="mb-4 text-lg font-semibold text-text-900">Historial</h2>
      {data && data.items.length === 0 ? (
        <p>Sin eventos registrados.</p>
      ) : (
        <ul className="space-y-2">
          {data?.items.map((evento) => (
            <li key={evento.id} className="text-sm">
              <span>{formatearInstante(evento.event_time)}</span>{" "}
              <span>{evento.action_label}</span>{" "}
              <span>{evento.username ?? "Sistema"}</span>
              {evento.reason && <span> · {evento.reason}</span>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function ImportacionDetallePage() {
  const { importId } = useParams<{ importId: string }>();
  const { activeCompany } = useCompany();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const [errorCancelacion, setErrorCancelacion] = useState<string | null>(null);
  const [motivoCancelacion, setMotivoCancelacion] = useState("");
  const [dialogoAbierto, setDialogoAbierto] = useState(false);

  const companyId = activeCompany?.id ?? "";

  const query = useQuery({
    queryKey: ["importaciones", importacionKey(companyId, importId ?? "")],
    queryFn: () => apiFetch<DetalleImportacion>(`/importaciones/${importId}`),
    refetchOnMount: "always",
  });

  const invalidar = () => queryClient.invalidateQueries({ queryKey: ["importaciones"] });

  if (query.isLoading) {
    return (
      <PageContent maxWidth="lg">
        <p>Cargando…</p>
      </PageContent>
    );
  }

  if (query.error || !query.data) {
    return (
      <PageContent maxWidth="lg">
        <div role="alert" className="rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600">
          Importación no encontrada en esta empresa.
        </div>
        <Link to="/compras/importaciones">
          <Button variant="secondary">Volver</Button>
        </Link>
      </PageContent>
    );
  }

  const detalle = query.data;

  const cancelar = async () => {
    if (!motivoCancelacion.trim()) {
      setErrorCancelacion("Indica el motivo de la cancelación.");
      return;
    }
    try {
      await apiFetch(`/importaciones/${detalle.id}/cancel`, {
        method: "POST",
        body: { reason: motivoCancelacion.trim() },
      });
      setDialogoAbierto(false);
      setMotivoCancelacion("");
      setErrorCancelacion(null);
      notify({ type: "success", title: "Importación cancelada." });
      invalidar();
    } catch (err) {
      setErrorCancelacion(err instanceof Error ? err.message : "Error al cancelar.");
    }
  };

  return (
    <PageContent maxWidth="lg">
      <PageHeader
        title={`${detalle.code} · ${detalle.supplier_name}`}
        status={ESTADOS[detalle.status]}
        crumbs={[
          { label: "Compras", to: "/compras" },
          { label: "Importaciones", to: "/compras/importaciones" },
          { label: detalle.code },
        ]}
        actions={
          detalle.allowed_actions.cancel ? (
            <Autorizado operacion={["POST", `/importaciones/${detalle.id}/cancel`]}>
              <Button variant="secondary" onClick={() => setDialogoAbierto(true)}>
                Cancelar importación
              </Button>
            </Autorizado>
          ) : undefined
        }
      />
      <ConfirmationDialog
        open={dialogoAbierto}
        title="Cancelar importación"
        description="Indica el motivo de la cancelación."
        confirmLabel="Cancelar importación"
        danger
        onConfirm={cancelar}
        onCancel={() => {
          setDialogoAbierto(false);
          setMotivoCancelacion("");
          setErrorCancelacion(null);
        }}
      >
        <TextInput
          aria-label="Motivo de la cancelación"
          value={motivoCancelacion}
          onChange={(e) => setMotivoCancelacion(e.target.value)}
        />
        {errorCancelacion && (
          <div role="alert" className="rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600">
            {errorCancelacion}
          </div>
        )}
      </ConfirmationDialog>
      <nav aria-label="Secciones del expediente" className="flex flex-wrap gap-x-4 gap-y-1">
        <a href="#resumen" className="text-sm font-medium text-brand-600 hover:text-brand-700">Resumen</a>
        <a href="#negociacion" className="text-sm font-medium text-brand-600 hover:text-brand-700">Negociación</a>
        <a href="#orden" className="text-sm font-medium text-brand-600 hover:text-brand-700">Orden</a>
        <a href="#documentacion" className="text-sm font-medium text-brand-600 hover:text-brand-700">Documentación</a>
        <a href="#seguimiento" className="text-sm font-medium text-brand-600 hover:text-brand-700">Seguimiento</a>
        <a href="#finanzas" className="text-sm font-medium text-brand-600 hover:text-brand-700">Finanzas</a>
        <a href="#correcciones" className="text-sm font-medium text-brand-600 hover:text-brand-700">Correcciones</a>
        <a href="#arribo" className="text-sm font-medium text-brand-600 hover:text-brand-700">Arribo</a>
        <a href="#recepcion" className="text-sm font-medium text-brand-600 hover:text-brand-700">Recepción</a>
        <a href="#diferencias" className="text-sm font-medium text-brand-600 hover:text-brand-700">Diferencias</a>
        <a href="#ubicacion" className="text-sm font-medium text-brand-600 hover:text-brand-700">Ubicación</a>
        <a href="#costos" className="text-sm font-medium text-brand-600 hover:text-brand-700">Costos</a>
        <a href="#historial" className="text-sm font-medium text-brand-600 hover:text-brand-700">Historial</a>
      </nav>
      <div className="space-y-6">
        <ImportacionResumen detalle={detalle} onCambios={invalidar} />
        <Negociacion detalle={detalle} onCambios={invalidar} />
        <VincularOrden key={`orden-${detalle.version}`} detalle={detalle} onCambios={invalidar} />
        <Documentos detalle={detalle} onCambios={invalidar} />
        <ImportacionSeguimiento key={`seguimiento-${detalle.version}`} detalle={detalle} onCambios={invalidar} />
        <ImportacionFinanzas detalle={detalle} onCambios={invalidar} />
        <ImportacionCorrecciones detalle={detalle} onCambios={invalidar} />
        {detalle.logistics && detalle.status === "DISPATCHED" ? (
          <>
            <ImportacionRecepcion detalle={detalle} onCambios={invalidar} />
            <ImportacionDiferencias detalle={detalle} />
            <ImportacionUbicacion detalle={detalle} onCambios={invalidar} />
          </>
        ) : null}
        {detalle.order_id && detalle.status !== "CANCELLED" ? (
          <ImportacionCostos detalle={detalle} onCambios={invalidar} />
        ) : null}

        <Autorizado operacion={["GET", `/importaciones/${detalle.id}/audit`]}>
          <Historial id={detalle.id} />
        </Autorizado>
      </div>
    </PageContent>
  );
}
