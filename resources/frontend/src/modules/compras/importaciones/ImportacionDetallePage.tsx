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
import {
  ESTADOS,
  ESTADOS_DOCUMENTO,
  INCOTERMS,
  importacionKey,
  type EstadoDocumento,
  type EstadoImportacion,
} from "./tipos";

type Documento = {
  id: string;
  kind: string;
  name: string;
  required: boolean;
  reference: string | null;
  status: EstadoDocumento;
  observation: string | null;
  version: number;
  attachments: unknown[];
  allowed_actions: {
    receive: boolean;
    validate: boolean;
    observe: boolean;
  };
};

type DetalleImportacion = {
  id: string;
  code: string;
  status: EstadoImportacion;
  currency: string;
  supplier_id: string;
  supplier_name: string;
  order_id: string | null;
  order_code: string | null;
  incoterm: string | null;
  incoterm_place: string | null;
  payment_conditions: string | null;
  delivery_conditions: string | null;
  expected_dispatch_date: string | null;
  expected_arrival_date: string | null;
  notes: string | null;
  cancel_reason: string | null;
  next_action: string | null;
  allowed_actions: {
    edit: boolean;
    link_order: boolean;
    add_document: boolean;
    confirm_documents: boolean;
    cancel: boolean;
  };
  documents: Documento[];
  version: number;
};

type EventoAuditoria = {
  id: string;
  action: string;
  action_label: string;
  event_time: string;
  username: string | null;
  reason: string | null;
  details: Record<string, unknown> | null;
};

type OrdenAprobada = {
  id: string;
  code: string;
  currency: string;
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
  const queryClient = useQueryClient();
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
      key={detalle.version}
      className="rounded-lg border border-border-default bg-surface-0 p-6"
    >
      <UnsavedChangesGuard hasUnsavedChanges={dirty && detalle.allowed_actions.edit} />
      <h2 className="mb-4 text-lg font-semibold text-text-900">Negociación</h2>
      <div className="grid gap-4 md:grid-cols-2">
        <FormField label="INCOTERM">
          <select
            className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
            value={form.incoterm}
            disabled={!detalle.allowed_actions.edit}
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
            disabled={!detalle.allowed_actions.edit}
            onChange={(e) => setCampo("incoterm_place", e.target.value)}
          />
        </FormField>
      </div>
      <FormField label="Condiciones de pago">
        <textarea
          className="min-h-20 w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
          value={form.payment_conditions}
          disabled={!detalle.allowed_actions.edit}
          onChange={(e) => setCampo("payment_conditions", e.target.value)}
        />
      </FormField>
      <FormField label="Condiciones de entrega">
        <textarea
          className="min-h-20 w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
          value={form.delivery_conditions}
          disabled={!detalle.allowed_actions.edit}
          onChange={(e) => setCampo("delivery_conditions", e.target.value)}
        />
      </FormField>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <FormField label="Despacho previsto">
          <TextInput
            type="date"
            value={form.expected_dispatch_date}
            disabled={!detalle.allowed_actions.edit}
            onChange={(e) => setCampo("expected_dispatch_date", e.target.value)}
          />
        </FormField>
        <FormField label="Llegada prevista">
          <TextInput
            type="date"
            value={form.expected_arrival_date}
            disabled={!detalle.allowed_actions.edit}
            onChange={(e) => setCampo("expected_arrival_date", e.target.value)}
          />
        </FormField>
      </div>
      <FormField label="Notas">
        <textarea
          className="min-h-20 w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
          value={form.notes}
          disabled={!detalle.allowed_actions.edit}
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
            onClick={() => queryClient.invalidateQueries({ queryKey: ["importaciones"] })}
          >
            Recargar
          </Button>
        </div>
      )}
      {detalle.allowed_actions.edit && (
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
  const [ordenId, setOrdenId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const ordenes = useQuery({
    queryKey: ["importaciones", "ordenes", detalle.supplier_id],
    enabled: detalle.allowed_actions.link_order,
    queryFn: () =>
      apiFetch<PagedResult<OrdenAprobada>>(
        `/purchasing/orders?status=APPROVED&supplier_id=${detalle.supplier_id}&page_size=100`,
      ),
  });

  const ordenesMoneda = (ordenes.data?.items ?? []).filter(
    (orden) => orden.currency === detalle.currency,
  );

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
    <section className="rounded-lg border border-border-default bg-surface-0 p-6">
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
        <>
          {ordenesMoneda.length === 0 ? (
            <p>
              Este proveedor no tiene órdenes aprobadas en esta moneda.{" "}
              <Link to="/compras/ordenes">Ver órdenes</Link>
            </p>
          ) : (
            <div className="flex items-end gap-3">
              <FormField label="Orden aprobada">
                <select
                  aria-label="Orden aprobada"
                  className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                  value={ordenId}
                  onChange={(e) => setOrdenId(e.target.value)}
                >
                  <option value="">Seleccionar…</option>
                  {ordenesMoneda.map((orden) => (
                    <option key={orden.id} value={orden.id}>
                      {orden.code}
                    </option>
                  ))}
                </select>
              </FormField>
              <Autorizado operacion={["POST", `/importaciones/${detalle.id}/order`]}>
                <AsyncButton disabled={!ordenId} onClick={vincular}>
                  Vincular orden
                </AsyncButton>
              </Autorizado>
            </div>
          )}
          {error && (
            <div role="alert" className="rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600">
              {error}
            </div>
          )}
        </>
      ) : null}
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
    <section className="rounded-lg border border-border-default bg-surface-0 p-6">
      <h2 className="mb-4 text-lg font-semibold text-text-900">Documentos</h2>
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
    <section className="rounded-lg border border-border-default bg-surface-0 p-6">
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
      <div className="space-y-6">
        <section role="status" className="rounded-lg border border-border-default bg-surface-0 p-6">
          <h2 className="mb-4 text-lg font-semibold text-text-900">Siguiente paso</h2>
          <p>{detalle.next_action ?? "Sin siguiente acción."}</p>
          {detalle.status === "CANCELLED" && detalle.cancel_reason && (
            <p className="mt-2 text-sm text-text-600">Motivo: {detalle.cancel_reason}</p>
          )}
        </section>
        <Negociacion detalle={detalle} onCambios={invalidar} />
        <VincularOrden key={`orden-${detalle.version}`} detalle={detalle} onCambios={invalidar} />
        <Documentos detalle={detalle} onCambios={invalidar} />
        <Autorizado operacion={["GET", `/importaciones/${detalle.id}/audit`]}>
          <Historial id={detalle.id} />
        </Autorizado>
      </div>
    </PageContent>
  );
}
