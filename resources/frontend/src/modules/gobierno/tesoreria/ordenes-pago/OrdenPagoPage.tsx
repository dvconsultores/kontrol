import { useState } from "react";
import { Link, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";
import { FormField } from "@/components/FormField";
import { formatearFechaDeNegocio, formatearInstante } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_ORDENES,
  RUTA_ORDENES,
  etiquetaControl,
  etiquetaEstadoOrden,
  formatearMonto,
  type Control,
  type OpcionesOrden,
  type OrdenPago,
} from "./api";

export function OrdenPagoPage() {
  const { ordenId } = useParams<{ ordenId: string }>();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();
  const [errorAccion, setErrorAccion] = useState<ApiError | string | null>(null);
  const [dialogoAbierto, setDialogoAbierto] = useState<"emitir" | "anular" | null>(null);
  const [motivoAnulacion, setMotivoAnulacion] = useState("");
  const [cargoAnulacion, setCargoAnulacion] = useState("");
  const [errorMotivo, setErrorMotivo] = useState(false);
  const [sodBloqueado, setSodBloqueado] = useState<{ activo: boolean; mensaje: string }>({
    activo: false,
    mensaje: "",
  });

  const puedeVer = tiene("gobierno_ordenes_pago:view", "empresa");
  const puedeGestionar = tiene("gobierno_ordenes_pago:manage", "empresa");
  const puedeEmitir = tiene("gobierno_ordenes_pago:issue", "empresa");
  const puedeAnular = tiene("gobierno_ordenes_pago:cancel", "empresa");

  const ordenQuery = useQuery({
    queryKey: [...CONSULTA_ORDENES, "detalle", ordenId],
    queryFn: () =>
      apiFetch<OrdenPago>(`/gobierno/tesoreria/ordenes-pago/${ordenId}`),
    enabled: puedeVer && Boolean(ordenId),
  });

  const opcionesQuery = useQuery({
    queryKey: [...CONSULTA_ORDENES, "opciones", ordenQuery.data?.year_id ?? ""],
    queryFn: () =>
      apiFetch<OpcionesOrden>(
        `/gobierno/tesoreria/ejercicios/${ordenQuery.data?.year_id ?? ""}/ordenes-pago/opciones`,
      ),
    enabled: puedeAnular && dialogoAbierto === "anular" && Boolean(ordenQuery.data?.year_id),
  });

  if (!puedeVer) {
    return (
      <PageContent>
        <EmptyState
          title="No tiene permiso para consultar órdenes de pago"
          description="Su rol no incluye la capacidad de consulta de órdenes de pago."
        />
      </PageContent>
    );
  }

  if (!ordenId) {
    return (
      <PageContent>
        <EmptyState title="Orden de pago no encontrada" />
      </PageContent>
    );
  }

  if (ordenQuery.isLoading) {
    return (
      <PageContent>
        <LoadingState label="Cargando orden de pago" />
      </PageContent>
    );
  }

  if (ordenQuery.isError) {
    const error = ordenQuery.error;
    if (error instanceof ApiError && error.status === 404) {
      return (
        <PageContent>
          <EmptyState
            title="Orden de pago no encontrada"
            description="La orden de pago solicitada no existe o no está disponible."
            action={<Link to={`${RUTA_ORDENES}/ordenes-pago`}>Volver a órdenes de pago</Link>}
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        <ErrorState
          title="No se pudo cargar la orden de pago"
          message={error instanceof Error ? error.message : "No se pudo completar la acción."}
          requestId={
            error instanceof ApiError ? error.requestId : undefined
          }
          onRetry={() => void ordenQuery.refetch()}
        />
      </PageContent>
    );
  }

  const orden = ordenQuery.data;
  if (!orden) {
    return (
      <PageContent>
        <EmptyState
          title="Orden de pago no encontrada"
          description="La orden de pago solicitada no existe o no está disponible."
          action={<Link to={`${RUTA_ORDENES}/ordenes-pago`}>Volver a órdenes de pago</Link>}
        />
      </PageContent>
    );
  }

  const titulo = orden.codigo ?? "Borrador de orden de pago";
  const controles = orden.controles?.controles ?? [];
  const controlesCompletos = orden.controles?.completo ?? false;

  const cerrarDialogo = () => {
    setDialogoAbierto(null);
    setMotivoAnulacion("");
    setCargoAnulacion("");
    setErrorMotivo(false);
  };

  const confirmarEmitir = async () => {
    try {
      const actualizada = await apiFetch<OrdenPago>(
        `/gobierno/tesoreria/ordenes-pago/${orden.id}/emitir`,
        { method: "POST", ifMatch: String(orden.version) },
      );
      cerrarDialogo();
      queryClient.setQueryData([...CONSULTA_ORDENES, "detalle", ordenId], actualizada);
      await queryClient.invalidateQueries({ queryKey: [...CONSULTA_ORDENES] });
      notify({ type: "success", title: "Orden de pago emitida" });
    } catch (error) {
      cerrarDialogo();
      if (error instanceof ApiError && error.code === "GOV_SOD_CONFLICT") {
        setSodBloqueado({ activo: true, mensaje: error.message });
      }
      setErrorAccion(error instanceof ApiError ? error : "No se pudo completar la acción.");
    }
  };

  const confirmarAnular = async () => {
    if (motivoAnulacion.trim().length < 10) {
      setErrorMotivo(true);
      return;
    }
    if (!cargoAnulacion) {
      setErrorAccion("Debe seleccionar el cargo que anula.");
      return;
    }
    try {
      const actualizada = await apiFetch<OrdenPago>(
        `/gobierno/tesoreria/ordenes-pago/${orden.id}/anular`,
        {
          method: "POST",
          ifMatch: String(orden.version),
          body: {
            motivo: motivoAnulacion.trim(),
            cargo_id: cargoAnulacion,
          },
        },
      );
      cerrarDialogo();
      queryClient.setQueryData([...CONSULTA_ORDENES, "detalle", ordenId], actualizada);
      await queryClient.invalidateQueries({ queryKey: [...CONSULTA_ORDENES] });
      notify({ type: "success", title: "Orden de pago anulada" });
    } catch (error) {
      cerrarDialogo();
      setErrorAccion(error instanceof ApiError ? error : "No se pudo completar la acción.");
    }
  };

  const mensajeErrorAccion = (error: ApiError | string): string => {
    if (error instanceof ApiError) {
      if (error.status === 409) {
        return `La orden cambió o una regla lo impide: ${error.message}`;
      }
      if (error.status === 403) {
        return "No tiene permiso para esta acción";
      }
      return error.message;
    }
    return error;
  };

  const estadoControl = (control: Control): React.ReactNode => {
    if (control.codigo === "SOD" && sodBloqueado.activo && !control.cumplido) {
      return "Bloqueado";
    }
    if (control.cumplido) {
      return "Cumple";
    }
    return "Falta";
  };

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno", to: "/gobierno" },
          { label: "Tesorería", to: RUTA_ORDENES },
          { label: "Órdenes de pago", to: `${RUTA_ORDENES}/ordenes-pago` },
          { label: titulo },
        ]}
        title={titulo}
        description={`Orden de pago del ejercicio ${orden.anio}`}
        status={
          <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
            {etiquetaEstadoOrden(orden.estado)}
          </span>
        }
        actions={
          <>
            {puedeGestionar && orden.estado === "BORRADOR" && (
              <Link
                to={`${RUTA_ORDENES}/ordenes-pago/${orden.id}/editar`}
                className="inline-flex items-center rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                Editar
              </Link>
            )}
            {puedeEmitir && orden.estado === "BORRADOR" && (
              <Button
                variant="primary"
                disabled={!controlesCompletos}
                onClick={() => setDialogoAbierto("emitir")}
              >
                Emitir orden de pago
              </Button>
            )}
            {puedeAnular && orden.estado === "EMITIDA" && (
              <Button variant="danger" onClick={() => setDialogoAbierto("anular")}>
                Anular
              </Button>
            )}
          </>
        }
      />

      {errorAccion && (
        <div role="alert" className="mb-4 rounded-md bg-red-50 p-4 text-sm text-red-800">
          <p>{mensajeErrorAccion(errorAccion)}</p>
          <Button
            variant="secondary"
            onClick={() => {
              setErrorAccion(null);
              setSodBloqueado({ activo: false, mensaje: "" });
              void ordenQuery.refetch();
            }}
          >
            Recargar
          </Button>
        </div>
      )}

      <section aria-labelledby="resumen-heading">
        <h2 id="resumen-heading" className="text-lg font-semibold">Resumen</h2>
        <dl className="mt-4 grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-slate-600">Fecha</dt>
            <dd className="mt-1 text-sm text-slate-900">
              {formatearFechaDeNegocio(orden.fecha_orden)}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Beneficiario</dt>
            <dd className="mt-1 text-sm text-slate-900">{orden.beneficiario ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Moneda</dt>
            <dd className="mt-1 text-sm text-slate-900">{orden.moneda}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Monto</dt>
            <dd className="mt-1 text-sm text-slate-900">
              {formatearMonto(orden.monto, orden.moneda)}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Política</dt>
            <dd className="mt-1 text-sm text-slate-900">
              {orden.policy.nombre} · {orden.policy.codigo} · versión {orden.policy.version}
            </dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-sm font-medium text-slate-600">Concepto</dt>
            <dd className="mt-1 text-sm text-slate-900">{orden.concepto}</dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="obligaciones-heading" className="mt-8">
        <h2 id="obligaciones-heading" className="text-lg font-semibold">
          Obligaciones causadas
        </h2>
        <div
          className="mt-4 overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Tabla de obligaciones de la orden"
        >
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                  Causado
                </th>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                  Compromiso
                </th>
                <th scope="col" className="px-3 py-2 text-right text-xs font-semibold text-slate-700">
                  Monto causado
                </th>
                <th scope="col" className="px-3 py-2 text-right text-xs font-semibold text-slate-700">
                  Monto ordenado
                </th>
                <th scope="col" className="px-3 py-2 text-right text-xs font-semibold text-slate-700">
                  Pendiente de ordenar
                </th>
                <th scope="col" className="px-3 py-2 text-right text-xs font-semibold text-slate-700">
                  Asignado en esta orden
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {orden.lineas.map((linea) => (
                <tr key={linea.cause_id}>
                  <td className="whitespace-nowrap px-3 py-2 text-sm">{linea.codigo}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-sm">
                    {linea.compromiso_codigo}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-right text-sm">
                    {linea.monto_causado}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-right text-sm">
                    {linea.monto_ordenado}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-right text-sm">
                    {linea.pendiente_de_ordenar}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-right text-sm">
                    {linea.monto_asignado}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="autoridad-heading" className="mt-8">
        <h2 id="autoridad-heading" className="text-lg font-semibold">Autoridad</h2>
        <dl className="mt-4 grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-slate-600">Cargo</dt>
            <dd className="mt-1 text-sm text-slate-900">{orden.autoridad.cargo ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Unidad</dt>
            <dd className="mt-1 text-sm text-slate-900">{orden.autoridad.unidad ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Funcionario</dt>
            <dd className="mt-1 text-sm text-slate-900">
              {orden.autoridad.funcionario ?? "—"}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Competencia</dt>
            <dd className="mt-1 text-sm text-slate-900">
              Competencia Ordenar pago × Tesorería
            </dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="documentos-heading" className="mt-8">
        <h2 id="documentos-heading" className="text-lg font-semibold">Documentos</h2>
        {orden.documentos.length === 0 ? (
          <p className="mt-4 text-sm text-slate-600">Sin documentos vinculados</p>
        ) : (
          <div
            className="mt-4 overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de documentos de soporte"
          >
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                    Título
                  </th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                    Tipo
                  </th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                    Huella
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {orden.documentos.map((documento) => (
                  <tr key={documento.document_id}>
                    <td className="px-3 py-2 text-sm">{documento.titulo}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-sm">
                      {documento.tipo ?? "—"}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-sm" title={documento.sha256 ?? ""}>
                      {documento.sha256 ? `${documento.sha256.slice(0, 12)}…` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {orden.estado === "BORRADOR" && (
        <section aria-labelledby="controles-heading" className="mt-8">
          <h2 id="controles-heading" className="text-lg font-semibold">Controles</h2>
          <ul className="mt-4 space-y-2">
            {controles.map((control) => (
              <li key={control.codigo} className="text-sm">
                {etiquetaControl(control.codigo)} · {estadoControl(control)}
                {control.codigo === "SOD" && sodBloqueado.activo && !control.cumplido
                  ? ` · ${sodBloqueado.mensaje}`
                  : ` · ${control.mensaje}`}
              </li>
            ))}
            <li className="text-sm text-slate-700">
              Segregación de funciones — Se verifica al emitir (CTL-01)
              {sodBloqueado.activo ? ` · Bloqueado · ${sodBloqueado.mensaje}` : ""}
            </li>
          </ul>
          {!controlesCompletos && orden.estado === "BORRADOR" && (
            <p className="mt-3 text-sm text-slate-700">
              Faltan requisitos: el sistema impedirá emitir hasta cumplirlos.
            </p>
          )}
        </section>
      )}

      <section aria-labelledby="frontera-heading" className="mt-8">
        <h2 id="frontera-heading" className="text-lg font-semibold">Frontera</h2>
        {orden.estado === "EMITIDA" && (
          <>
            <p className="mt-3 text-sm">
              Siguiente paso: {orden.siguiente_paso ?? "Pago (TRE-04)"}
            </p>
            <p className="mt-2 text-sm">
              Pendiente de pagar: {formatearMonto(orden.pendiente_de_pagar, orden.moneda)}
            </p>
            {orden.emitida_en && (
              <p className="mt-2 text-sm">
                Emitida el {formatearInstante(orden.emitida_en)} por {orden.emitida_por ?? "—"}
              </p>
            )}
          </>
        )}
        {orden.estado === "BORRADOR" && (
          <p className="mt-3 text-sm">
            Al emitir se asigna número y la orden queda inmutable.
          </p>
        )}
        {orden.estado === "ANULADA" && (
          <p className="mt-3 text-sm">
            {orden.anulada_en
              ? `Anulada el ${formatearInstante(orden.anulada_en)}. `
              : "Anulada. "}
            Motivo: {orden.motivo_anulacion ?? "—"}
          </p>
        )}
      </section>

      <section aria-labelledby="historia-heading" className="mt-8">
        <h2 id="historia-heading" className="text-lg font-semibold">Historia</h2>
        {orden.historia.length === 0 ? (
          <p className="mt-4 text-sm text-slate-600">Sin eventos</p>
        ) : (
          <div
            className="mt-4 overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de eventos de la orden"
          >
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                    Evento
                  </th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                    Fecha
                  </th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                    Actor
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {orden.historia.map((evento) => (
                  <tr key={`${evento.evento}-${evento.fecha}-${evento.actor}`}>
                    <td className="whitespace-nowrap px-3 py-2 text-sm">{evento.evento}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-sm">
                      {formatearInstante(evento.fecha)}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-sm">{evento.actor}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <ConfirmationDialog
        open={dialogoAbierto === "emitir"}
        title="Emitir orden de pago"
        description={`Se emitirá una orden de pago de ${formatearMonto(orden.monto, orden.moneda)} a favor de ${orden.beneficiario ?? "—"}. La orden quedará emitida e inmutable; solo puede anularse.`}
        confirmLabel="Emitir"
        onConfirm={confirmarEmitir}
        onCancel={cerrarDialogo}
      />

      <ConfirmationDialog
        open={dialogoAbierto === "anular"}
        title="Anular la orden de pago"
        description="El monto vuelve a quedar pendiente de ordenar en los causados."
        confirmLabel="Anular"
        danger
        onConfirm={confirmarAnular}
        onCancel={cerrarDialogo}
      >
        <FormField label="Motivo de la anulación" htmlFor="orden-anulacion-motivo">
          <textarea
            id="orden-anulacion-motivo"
            value={motivoAnulacion}
            onChange={(event) => {
              setMotivoAnulacion(event.target.value);
              setErrorMotivo(false);
            }}
            maxLength={500}
            className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </FormField>
        <p className="mt-1 text-xs text-slate-500">Entre 10 y 500 caracteres</p>
        {errorMotivo && (
          <div role="alert" className="mt-2 text-sm text-red-700">
            El motivo debe tener al menos 10 caracteres
          </div>
        )}

        <FormField label="Cargo que anula" htmlFor="orden-anulacion-cargo">
          <select
            id="orden-anulacion-cargo"
            value={cargoAnulacion}
            onChange={(event) => setCargoAnulacion(event.target.value)}
            className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">Seleccione un cargo</option>
            {(opcionesQuery.data?.cargos ?? []).map((cargo) => (
              <option key={cargo.id} value={cargo.id}>
                {cargo.nombre}
              </option>
            ))}
          </select>
        </FormField>
      </ConfirmationDialog>
    </PageContent>
  );
}
