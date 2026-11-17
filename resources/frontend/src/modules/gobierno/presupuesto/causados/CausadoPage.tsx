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
import { formatearFechaDeNegocio, formatearInstante } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_CAUSADOS,
  RUTA_CAUSADOS,
  DISPARADORES,
  type Causado,
} from "./api";

const ETIQUETAS_ESTADO: Record<Causado["estado"], string> = {
  BORRADOR: "Borrador",
  FORMALIZADO: "Formalizado",
  ANULADO: "Anulado",
};

const ETIQUETAS_EVIDENCIA: Record<string, string> = {
  CONTRACT_RECEIPT: "Recepción",
  CONTRACT_VALUATION: "Valuación",
  CONTRACT_DELIVERY: "Entrega",
  CONTRACT_INVOICE: "Factura",
  DOCUMENT: "Documento",
};

function etiquetaEvidencia(tipo: string): string {
  return ETIQUETAS_EVIDENCIA[tipo] ?? tipo;
}

export function CausadoPage() {
  const { causadoId } = useParams<{ causadoId: string }>();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();
  const [errorAccion, setErrorAccion] = useState<ApiError | string | null>(null);
  const [dialogoAbierto, setDialogoAbierto] = useState<"formalizar" | "anular" | null>(null);
  const [motivoAnulacion, setMotivoAnulacion] = useState("");
  const [errorMotivo, setErrorMotivo] = useState(false);

  const puedeVer = tiene("gobierno_presupuesto:view", "empresa");
  const puedeCausar = tiene("gobierno_presupuesto:cause", "empresa");

  const causadoQuery = useQuery({
    queryKey: [...CONSULTA_CAUSADOS, "detalle", causadoId],
    queryFn: () =>
      apiFetch<Causado>(`/gobierno/presupuesto/causados/${causadoId}`),
    enabled: puedeVer && Boolean(causadoId),
  });

  if (!puedeVer) {
    return (
      <PageContent>
        <EmptyState title="Sin acceso" />
      </PageContent>
    );
  }

  if (!causadoId) {
    return (
      <PageContent>
        <EmptyState title="Causado no encontrado" />
      </PageContent>
    );
  }

  if (causadoQuery.isLoading) {
    return (
      <PageContent>
        <LoadingState label="Cargando causado" />
      </PageContent>
    );
  }

  if (causadoQuery.isError) {
    const error = causadoQuery.error;
    if (error instanceof ApiError && error.status === 404) {
      return (
        <PageContent>
          <EmptyState
            title="Causado no encontrado"
            description="El causado solicitado no existe o no está disponible."
            action={<Link to={RUTA_CAUSADOS}>Volver a causados</Link>}
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        <ErrorState
          title="No se pudo cargar el causado"
          message={error instanceof Error ? error.message : "No se pudo completar la acción."}
          onRetry={() => void causadoQuery.refetch()}
        />
      </PageContent>
    );
  }

  const causado = causadoQuery.data;
  if (!causado) {
    return (
      <PageContent>
        <EmptyState
          title="Causado no encontrado"
          description="El causado solicitado no existe o no está disponible."
          action={<Link to={RUTA_CAUSADOS}>Volver a causados</Link>}
        />
      </PageContent>
    );
  }

  const titulo = causado.codigo ?? "Borrador de causado";
  const cumpleControles = causado.controles.every((control) => control.cumplido);

  const cerrarDialogo = () => {
    setDialogoAbierto(null);
    setMotivoAnulacion("");
    setErrorMotivo(false);
  };

  const confirmarFormalizar = async () => {
    try {
      const actualizado = await apiFetch<Causado>(
        `/gobierno/presupuesto/causados/${causado.id}/formalizar`,
        { method: "POST", ifMatch: String(causado.version) },
      );
      cerrarDialogo();
      queryClient.setQueryData([...CONSULTA_CAUSADOS, "detalle", causadoId], actualizado);
      await queryClient.invalidateQueries({ queryKey: [...CONSULTA_CAUSADOS] });
      notify({ type: "success", title: "Causado formalizado" });
    } catch (error) {
      cerrarDialogo();
      setErrorAccion(error instanceof ApiError ? error : "No se pudo completar la acción.");
    }
  };

  const confirmarAnular = async () => {
    if (motivoAnulacion.trim().length < 10) {
      setErrorMotivo(true);
      return;
    }
    try {
      const actualizado = await apiFetch<Causado>(
        `/gobierno/presupuesto/causados/${causado.id}/anular`,
        {
          method: "POST",
          ifMatch: String(causado.version),
          body: { motivo: motivoAnulacion.trim() },
        },
      );
      cerrarDialogo();
      queryClient.setQueryData([...CONSULTA_CAUSADOS, "detalle", causadoId], actualizado);
      await queryClient.invalidateQueries({ queryKey: [...CONSULTA_CAUSADOS] });
      notify({ type: "success", title: "Causado anulado" });
    } catch (error) {
      cerrarDialogo();
      setErrorAccion(error instanceof ApiError ? error : "No se pudo completar la acción.");
    }
  };

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Causados", to: RUTA_CAUSADOS },
          { label: titulo },
        ]}
        title={titulo}
        description={`Causado del ejercicio ${causado.anio}`}
        status={
          <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
            {ETIQUETAS_ESTADO[causado.estado]}
          </span>
        }
        actions={
          puedeCausar ? (
            <>
              {causado.estado === "BORRADOR" && (
                <>
                  <Link
                    to={`${RUTA_CAUSADOS}/${causado.id}/editar`}
                    className="inline-flex items-center rounded-md border border-slate-300 px-3 py-2 text-sm"
                  >
                    Editar
                  </Link>
                  <Button variant="primary" onClick={() => setDialogoAbierto("formalizar")}>
                    Formalizar
                  </Button>
                </>
              )}
              {causado.estado === "FORMALIZADO" && (
                <Button variant="danger" onClick={() => setDialogoAbierto("anular")}>
                  Anular
                </Button>
              )}
            </>
          ) : undefined
        }
      />

      {errorAccion && (
        <div role="alert" className="mb-4 rounded-md bg-red-50 p-4 text-sm text-red-800">
          <p>
            {errorAccion instanceof ApiError
              ? errorAccion.message
              : errorAccion}
          </p>
          {errorAccion instanceof ApiError && errorAccion.code === "GOV_BUDGET_CAUSE_STALE" && (
            <Button
              variant="secondary"
              onClick={() => {
                setErrorAccion(null);
                void causadoQuery.refetch();
              }}
            >
              Recargar
            </Button>
          )}
        </div>
      )}

      <section aria-labelledby="resumen-heading">
        <h2 id="resumen-heading" className="text-lg font-semibold">Resumen</h2>
        <dl className="mt-4 grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-slate-600">Concepto</dt>
            <dd className="mt-1 text-sm text-slate-900">{causado.concepto}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Beneficiario</dt>
            <dd className="mt-1 text-sm text-slate-900">{causado.beneficiario ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Compromiso</dt>
            <dd className="mt-1 text-sm text-slate-900">
              {causado.compromiso.codigo} · {causado.compromiso.concepto}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Monto</dt>
            <dd className="mt-1 text-sm text-slate-900">
              {causado.monto} {causado.moneda}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Fecha efectiva</dt>
            <dd className="mt-1 text-sm text-slate-900">
              {formatearFechaDeNegocio(causado.fecha_efectiva)}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Registrado el</dt>
            <dd className="mt-1 text-sm text-slate-900">
              {formatearInstante(causado.registrado_en)}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Política</dt>
            <dd className="mt-1 text-sm text-slate-900">
              {causado.politica.nombre} · {causado.politica.tipo_gasto} ·{" "}
              {DISPARADORES[causado.politica.disparador]} · versión {causado.politica.version}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Autoridad</dt>
            <dd className="mt-1 text-sm text-slate-900">
              {causado.autoridad
                ? `${causado.autoridad.cargo} · ${causado.autoridad.unidad} · ${causado.autoridad.funcionario}`
                : "Se indicará al formalizar"}
            </dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="imputacion-heading" className="mt-8">
        <h2 id="imputacion-heading" className="text-lg font-semibold">Imputación</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">Partida</th>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">Categoría</th>
                <th scope="col" className="px-3 py-2 text-right text-xs font-semibold text-slate-700">Comprometido</th>
                <th scope="col" className="px-3 py-2 text-right text-xs font-semibold text-slate-700">Causado por otros</th>
                <th scope="col" className="px-3 py-2 text-right text-xs font-semibold text-slate-700">Este causado</th>
                <th scope="col" className="px-3 py-2 text-right text-xs font-semibold text-slate-700">Pendiente tras</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {causado.lineas.map((linea) => (
                <tr key={linea.id}>
                  <td className="whitespace-nowrap px-3 py-2 text-sm">{linea.partida}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-sm">{linea.categoria}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-right text-sm">{linea.comprometido}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-right text-sm">{linea.causado_otros}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-right text-sm">{linea.monto}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-right text-sm">{linea.pendiente_tras}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-sm">
          Pendiente del compromiso: {causado.compromiso.pendiente} {causado.moneda}
        </p>
      </section>

      <section aria-labelledby="respaldo-heading" className="mt-8">
        <h2 id="respaldo-heading" className="text-lg font-semibold">Respaldo</h2>
        {causado.evidencias.length === 0 ? (
          <p className="mt-4 text-sm text-slate-600">Sin evidencias vinculadas</p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">Tipo</th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">Evidencia</th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">Estado</th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">Fecha</th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">Huella</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {causado.evidencias.map((evidencia) => (
                  <tr key={evidencia.id}>
                    <td className="whitespace-nowrap px-3 py-2 text-sm">
                      {etiquetaEvidencia(evidencia.tipo)}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-sm">{evidencia.etiqueta}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-sm">{evidencia.estado}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-sm">
                      {formatearFechaDeNegocio(evidencia.fecha)}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-sm" title={evidencia.sha256}>
                      {evidencia.sha256.slice(0, 12)}…
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {causado.estado === "BORRADOR" && (
        <section aria-labelledby="controles-heading" className="mt-8">
          <h2 id="controles-heading" className="text-lg font-semibold">Controles</h2>
          <ul className="mt-4 space-y-2">
            {causado.controles.map((control) => (
              <li key={control.codigo} className="text-sm">
                {control.cumplido ? "✓ Cumplido" : "✗ Pendiente"} · {control.mensaje}
              </li>
            ))}
          </ul>
          {!cumpleControles && (
            <p className="mt-3 text-sm text-slate-700">
              Faltan requisitos: el sistema impedirá formalizar hasta cumplirlos.
            </p>
          )}
        </section>
      )}

      <section aria-labelledby="que-sigue-heading" className="mt-8">
        <h2 id="que-sigue-heading" className="text-lg font-semibold">Qué sigue</h2>
        {causado.estado === "BORRADOR" && (
          <p className="mt-3 text-sm">
            Al formalizar se asigna número y el causado queda inmutable.
          </p>
        )}
        {causado.estado === "FORMALIZADO" && (
          <>
            <p className="mt-3 text-sm">
              Pendiente de orden de pago: {causado.pendiente_de_ordenar} {causado.moneda}. La
              orden de pago se emite en Tesorería (TRE-03).
            </p>
            {causado.formalizado_en && (
              <p className="mt-2 text-sm">
                Formalizado el {formatearInstante(causado.formalizado_en)}
              </p>
            )}
          </>
        )}
        {causado.estado === "ANULADO" && (
          <p className="mt-3 text-sm">
            {causado.anulado_en
              ? `Anulado el ${formatearInstante(causado.anulado_en)}. `
              : "Anulado. "}
            Motivo: {causado.motivo_anulacion ?? "—"}
          </p>
        )}
      </section>

      <section aria-labelledby="historia-heading" className="mt-8">
        <h2 id="historia-heading" className="text-lg font-semibold">Historia</h2>
        {causado.historia.length === 0 ? (
          <p className="mt-4 text-sm text-slate-600">Sin eventos</p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">Evento</th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">Fecha</th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">Actor</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {causado.historia.map((evento) => (
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
        open={dialogoAbierto === "formalizar"}
        title="Formalizar el causado"
        description={`Se formalizará un causado de ${causado.monto} ${causado.moneda} contra el compromiso ${causado.compromiso.codigo}. Esta acción no se puede deshacer; solo puede anularse.`}
        confirmLabel="Formalizar"
        onConfirm={confirmarFormalizar}
        onCancel={cerrarDialogo}
      />

      <ConfirmationDialog
        open={dialogoAbierto === "anular"}
        title="Anular el causado"
        confirmLabel="Anular"
        danger
        onConfirm={confirmarAnular}
        onCancel={cerrarDialogo}
      >
        <label className="block text-sm font-medium text-slate-700">
          Motivo
          <textarea
            value={motivoAnulacion}
            onChange={(event) => {
              setMotivoAnulacion(event.target.value);
              setErrorMotivo(false);
            }}
            maxLength={500}
            className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <p className="mt-1 text-xs text-slate-500">Entre 10 y 500 caracteres</p>
        {errorMotivo && (
          <div role="alert" className="mt-2 text-sm text-red-700">
            El motivo debe tener al menos 10 caracteres
          </div>
        )}
      </ConfirmationDialog>
    </PageContent>
  );
}
