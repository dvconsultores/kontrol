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
import { RetencionesPago } from "@/modules/gobierno/tesoreria/retenciones/RetencionesPago";
import { formatearFechaDeNegocio, formatearInstante, hoyDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_PAGOS,
  ESTADOS_PAGO,
  ETAPAS_DOCUMENTO_PAGO,
  RUTA_PAGOS,
  type AprobacionPago,
  type ControlPago,
  type OpcionesPago,
  type Pago,
} from "./api";

interface RequisitoPendiente {
  indice: number;
  accion: string;
  materia: string;
  cantidad: number;
}

export function PagoPage() {
  const { pagoId } = useParams<{ pagoId: string }>();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();
  const [errorAccion, setErrorAccion] = useState<ApiError | string | null>(null);
  const [dialogoAbierto, setDialogoAbierto] = useState<
    "enviar" | "descartar" | "aprobar" | "rechazar" | "registrar" | "anular" | "duplicado" | null
  >(null);
  const [motivo, setMotivo] = useState("");
  const [errorMotivo, setErrorMotivo] = useState(false);
  const [cargoId, setCargoId] = useState("");
  const [requisitoIndice, setRequisitoIndice] = useState("");
  const [fechaValor, setFechaValor] = useState("");
  const [referenciaExterna, setReferenciaExterna] = useState("");
  const [errorFechaValor, setErrorFechaValor] = useState(false);
  const [errorReferencia, setErrorReferencia] = useState(false);
  const [errorCargo, setErrorCargo] = useState(false);

  const puedeVer = tiene("gobierno_pagos:view", "empresa");
  const puedeGestionar = tiene("gobierno_pagos:manage", "empresa");
  const puedeAutorizar = tiene("gobierno_pagos:authorize", "empresa");
  const puedeEjecutar = tiene("gobierno_pagos:execute", "empresa");
  const puedeAnular = tiene("gobierno_pagos:cancel", "empresa");

  const pagoQuery = useQuery({
    queryKey: [...CONSULTA_PAGOS, "detalle", pagoId],
    queryFn: () => apiFetch<Pago>(`${RUTA_PAGOS}/${pagoId}`),
    enabled: puedeVer && Boolean(pagoId),
  });

  const opcionesQuery = useQuery({
    queryKey: [...CONSULTA_PAGOS, "opciones"],
    queryFn: () => apiFetch<OpcionesPago>(`${RUTA_PAGOS}/opciones`),
    enabled:
      puedeVer &&
      Boolean(
        dialogoAbierto === "enviar" ||
          dialogoAbierto === "aprobar" ||
          dialogoAbierto === "rechazar",
      ),
  });

  const requisitosPendientes: RequisitoPendiente[] = ((pagoQuery.data?.regla as {
    banda?: { requisitos?: { accion: string; materia: string; cantidad: number }[] };
  } | null)?.banda?.requisitos ?? []).reduce<RequisitoPendiente[]>((acumulador, requisito, indice) => {
    const aprobadas = (pagoQuery.data?.aprobaciones ?? []).filter(
      (aprobacion) => aprobacion.decision === "APROBADA" && aprobacion.requisito_indice === indice,
    ).length;
    const faltan = requisito.cantidad - aprobadas;
    if (faltan > 0) {
      acumulador.push({
        indice,
        accion: requisito.accion,
        materia: requisito.materia,
        cantidad: faltan,
      });
    }
    return acumulador;
  }, []);

  const aprobacionesRealizadas =
    pagoQuery.data?.aprobaciones.filter((a) => a.decision === "APROBADA").length ?? 0;

  if (!puedeVer) {
    return (
      <PageContent>
        <EmptyState
          title="No tiene permiso para consultar pagos"
          description="Su rol no incluye la capacidad de consulta de pagos."
        />
      </PageContent>
    );
  }

  if (!pagoId) {
    return (
      <PageContent>
        <EmptyState title="Pago no encontrado" />
      </PageContent>
    );
  }

  if (pagoQuery.isLoading) {
    return (
      <PageContent>
        <LoadingState label="Cargando pago" />
      </PageContent>
    );
  }

  if (pagoQuery.isError) {
    const error = pagoQuery.error;
    if (error instanceof ApiError && error.status === 404) {
      return (
        <PageContent>
          <EmptyState
            title="Pago no encontrado"
            description="El pago solicitado no existe o no está disponible."
            action={<Link to={RUTA_PAGOS}>Volver a pagos</Link>}
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        <ErrorState
          title="No se pudo cargar el pago"
          message={error instanceof Error ? error.message : "No se pudo completar la acción."}
          requestId={error instanceof ApiError ? error.requestId : undefined}
          onRetry={() => void pagoQuery.refetch()}
        />
      </PageContent>
    );
  }

  const pago = pagoQuery.data;
  if (!pago) {
    return (
      <PageContent>
        <EmptyState
          title="Pago no encontrado"
          description="El pago solicitado no existe o no está disponible."
          action={<Link to={RUTA_PAGOS}>Volver a pagos</Link>}
        />
      </PageContent>
    );
  }

  const titulo = `Pago ${pago.codigo ?? "en borrador"}`;
  const regla = pago.regla as {
    banda?: {
      monto_desde?: string;
      monto_hasta?: string | null;
      requisitos?: { accion: string; materia: string; cantidad: number }[];
    };
    aprobaciones_requeridas?: number;
    control_duplicado?: string;
    permite_pago_parcial?: boolean;
    autorizador_firmante?: boolean;
  } | null;

  const cerrarDialogo = () => {
    setDialogoAbierto(null);
    setMotivo("");
    setErrorMotivo(false);
    setCargoId("");
    setRequisitoIndice("");
    setFechaValor("");
    setReferenciaExterna("");
    setErrorFechaValor(false);
    setErrorReferencia(false);
    setErrorCargo(false);
  };

  const notificarError = (error: unknown) => {
    cerrarDialogo();
    setErrorAccion(error instanceof ApiError ? error : "No se pudo completar la acción.");
  };

  const actualizarPago = (actualizado: Pago) => {
    queryClient.setQueryData([...CONSULTA_PAGOS, "detalle", pagoId], actualizado);
    void queryClient.invalidateQueries({ queryKey: [...CONSULTA_PAGOS] });
  };

  const confirmarEnviar = async (confirmarDuplicado = false, motivoDuplicado = "") => {
    try {
      const actualizado = await apiFetch<Pago>(`${RUTA_PAGOS}/${pago.id}/enviar`, {
        method: "POST",
        ifMatch: String(pago.version),
        body: {
          preparador_cargo_id: cargoId || null,
          confirmar_duplicado: confirmarDuplicado,
          motivo_duplicado: motivoDuplicado || null,
        },
      });
      cerrarDialogo();
      actualizarPago(actualizado);
      notify({ type: "success", title: "Pago enviado a autorización" });
    } catch (error) {
      if (
        !confirmarDuplicado &&
        error instanceof ApiError &&
        error.code === "GOV_PAYMENT_DUPLICATE_CONFIRMATION_REQUIRED"
      ) {
        setErrorAccion(null);
        setDialogoAbierto("duplicado");
        return;
      }
      notificarError(error);
    }
  };

  const confirmarDescartar = async () => {
    try {
      const actualizado = await apiFetch<Pago>(`${RUTA_PAGOS}/${pago.id}/descartar`, {
        method: "POST",
        ifMatch: String(pago.version),
      });
      cerrarDialogo();
      actualizarPago(actualizado);
      notify({ type: "success", title: "Borrador de pago descartado" });
    } catch (error) {
      notificarError(error);
    }
  };

  const confirmarAprobar = async () => {
    if (!cargoId) {
      setErrorCargo(true);
      return;
    }
    try {
      const actualizado = await apiFetch<Pago>(`${RUTA_PAGOS}/${pago.id}/aprobar`, {
        method: "POST",
        ifMatch: String(pago.version),
        body: {
          cargo_id: cargoId,
          requisito_indice: requisitoIndice ? Number(requisitoIndice) : null,
          documentos: [],
        },
      });
      cerrarDialogo();
      actualizarPago(actualizado);
      notify({ type: "success", title: "Pago aprobado" });
    } catch (error) {
      notificarError(error);
    }
  };

  const confirmarRechazar = async () => {
    if (!cargoId) {
      setErrorCargo(true);
      return;
    }
    if (motivo.trim().length < 10) {
      setErrorMotivo(true);
      return;
    }
    try {
      const actualizado = await apiFetch<Pago>(`${RUTA_PAGOS}/${pago.id}/rechazar`, {
        method: "POST",
        ifMatch: String(pago.version),
        body: {
          cargo_id: cargoId,
          motivo: motivo.trim(),
          documentos: [],
        },
      });
      cerrarDialogo();
      actualizarPago(actualizado);
      notify({ type: "success", title: "Pago rechazado" });
    } catch (error) {
      notificarError(error);
    }
  };

  const confirmarRegistrar = async () => {
    let valido = true;
    if (!fechaValor) {
      setErrorFechaValor(true);
      valido = false;
    }
    if (pago.medio.exige_referencia && referenciaExterna.trim().length === 0) {
      setErrorReferencia(true);
      valido = false;
    }
    if (!valido) {
      return;
    }
    try {
      const actualizado = await apiFetch<Pago>(`${RUTA_PAGOS}/${pago.id}/registrar`, {
        method: "POST",
        ifMatch: String(pago.version),
        body: {
          fecha_valor: fechaValor,
          referencia_externa: referenciaExterna.trim() || null,
          documentos: [],
          idempotency_key: crypto.randomUUID(),
        },
      });
      cerrarDialogo();
      actualizarPago(actualizado);
      notify({ type: "success", title: "Pago registrado como ejecutado" });
    } catch (error) {
      notificarError(error);
    }
  };

  const confirmarAnular = async () => {
    if (motivo.trim().length < 10) {
      setErrorMotivo(true);
      return;
    }
    try {
      const actualizado = await apiFetch<Pago>(`${RUTA_PAGOS}/${pago.id}/anular`, {
        method: "POST",
        ifMatch: String(pago.version),
        body: {
          motivo: motivo.trim(),
          documentos: [],
        },
      });
      cerrarDialogo();
      actualizarPago(actualizado);
      notify({ type: "success", title: "Pago anulado antes de ejecutar" });
    } catch (error) {
      notificarError(error);
    }
  };

  const confirmarDuplicado = async () => {
    if (motivo.trim().length < 10) {
      setErrorMotivo(true);
      return;
    }
    try {
      const actualizado = await apiFetch<Pago>(`${RUTA_PAGOS}/${pago.id}/enviar`, {
        method: "POST",
        ifMatch: String(pago.version),
        body: {
          preparador_cargo_id: cargoId || null,
          confirmar_duplicado: true,
          motivo_duplicado: motivo.trim(),
        },
      });
      cerrarDialogo();
      actualizarPago(actualizado);
      notify({ type: "success", title: "Pago enviado a autorización" });
    } catch (error) {
      notificarError(error);
    }
  };

  const mensajeErrorAccion = (error: ApiError | string): string => {
    if (error instanceof ApiError) {
      if (error.status === 409) {
        return `El pago cambió o una regla lo impide: ${error.message}`;
      }
      if (error.status === 403) {
        return "No tiene permiso para esta acción";
      }
      return error.message;
    }
    return error;
  };

  const estadoControl = (control: ControlPago): string => {
    if (control.cumplido) {
      return "Cumple";
    }
    return "Falta";
  };

  const formatearMonto = (monto: string, moneda: string): string =>
    `${monto} ${moneda}`;

  const abrirAprobar = () => {
    setCargoId("");
    setRequisitoIndice("");
    setErrorCargo(false);
    setDialogoAbierto("aprobar");
  };

  const abrirRechazar = () => {
    setCargoId("");
    setMotivo("");
    setErrorCargo(false);
    setErrorMotivo(false);
    setDialogoAbierto("rechazar");
  };

  const abrirRegistrar = () => {
    setFechaValor(hoyDeNegocio());
    setReferenciaExterna("");
    setErrorFechaValor(false);
    setErrorReferencia(false);
    setDialogoAbierto("registrar");
  };

  const abrirAnular = () => {
    setMotivo("");
    setErrorMotivo(false);
    setDialogoAbierto("anular");
  };

  const abrirEnviar = () => {
    setCargoId("");
    setErrorCargo(false);
    setDialogoAbierto("enviar");
  };

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno", to: "/gobierno" },
          { label: "Tesorería", to: RUTA_PAGOS },
          { label: "Pagos", to: RUTA_PAGOS },
          { label: titulo },
        ]}
        title={titulo}
        description={`Pago del ejercicio ${pago.orden?.codigo ?? ""}`}
        status={
          <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
            {ESTADOS_PAGO[pago.estado]}
          </span>
        }
        actions={
          <>
            {puedeGestionar && pago.estado === "BORRADOR" && (
              <Link
                to={`${RUTA_PAGOS}/${pago.id}/editar`}
                className="inline-flex items-center rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                Editar
              </Link>
            )}
            {puedeGestionar && pago.estado === "BORRADOR" && (
              <>
                <Button variant="primary" onClick={abrirEnviar}>
                  Enviar a autorización
                </Button>
                <Button variant="danger" onClick={() => setDialogoAbierto("descartar")}>
                  Descartar borrador
                </Button>
              </>
            )}
            {puedeAutorizar && pago.estado === "PENDIENTE_AUTORIZACION" && (
              <>
                <Button variant="primary" onClick={abrirAprobar}>
                  Aprobar
                </Button>
                <Button variant="danger" onClick={abrirRechazar}>
                  Rechazar
                </Button>
              </>
            )}
            {puedeEjecutar && pago.estado === "AUTORIZADO" && (
              <Button variant="primary" onClick={abrirRegistrar}>
                Registrar pago ejecutado
              </Button>
            )}
            {puedeAnular &&
              (pago.estado === "PENDIENTE_AUTORIZACION" || pago.estado === "AUTORIZADO") && (
                <Button variant="danger" onClick={abrirAnular}>
                  Anular antes de ejecutar
                </Button>
              )}
          </>
        }
      />

      {errorAccion && (
        <div role="alert" className="mb-4 rounded-md bg-red-50 p-4 text-sm text-red-800">
          <p>{mensajeErrorAccion(errorAccion)}</p>
          <Button variant="secondary" onClick={() => setErrorAccion(null)}>
            Cerrar
          </Button>
        </div>
      )}

      <section aria-labelledby="orden-pago-heading">
        <h2 id="orden-pago-heading" className="text-lg font-semibold">Orden de pago</h2>
        <dl className="mt-4 grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-slate-600">Código</dt>
            <dd className="mt-1 text-sm text-slate-900">{pago.orden.codigo ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Beneficiario</dt>
            <dd className="mt-1 text-sm text-slate-900">{pago.orden.beneficiario ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Moneda</dt>
            <dd className="mt-1 text-sm text-slate-900">{pago.orden.moneda}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Ordenado</dt>
            <dd className="mt-1 text-sm text-slate-900">
              {formatearMonto(pago.orden.monto_ordenado, pago.orden.moneda)}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Pagado</dt>
            <dd className="mt-1 text-sm text-slate-900">
              {formatearMonto(pago.orden.monto_pagado, pago.orden.moneda)}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">En trámite</dt>
            <dd className="mt-1 text-sm text-slate-900">
              {formatearMonto(pago.orden.monto_en_tramite, pago.orden.moneda)}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Pendiente de pagar</dt>
            <dd className="mt-1 text-sm text-slate-900">
              {formatearMonto(pago.orden.pendiente_de_pagar, pago.orden.moneda)}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Disponible para un nuevo pago</dt>
            <dd className="mt-1 text-sm text-slate-900">
              {formatearMonto(pago.orden.disponible_para_pago, pago.orden.moneda)}
            </dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="pago-heading" className="mt-8">
        <h2 id="pago-heading" className="text-lg font-semibold">Pago</h2>
        <dl className="mt-4 grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-slate-600">Cuenta</dt>
            <dd className="mt-1 text-sm text-slate-900">
              {pago.cuenta.codigo} · {pago.cuenta.denominacion} · {pago.cuenta.numero_enmascarado}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Medio</dt>
            <dd className="mt-1 text-sm text-slate-900">{pago.medio.nombre}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Monto y moneda</dt>
            <dd className="mt-1 text-sm text-slate-900">
              {formatearMonto(pago.monto, pago.moneda)}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Fecha de pago</dt>
            <dd className="mt-1 text-sm text-slate-900">
              {formatearFechaDeNegocio(pago.fecha_pago)}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Fecha valor</dt>
            <dd className="mt-1 text-sm text-slate-900">
              {pago.fecha_valor ? formatearFechaDeNegocio(pago.fecha_valor) : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Referencia externa</dt>
            <dd className="mt-1 text-sm text-slate-900">{pago.referencia_externa ?? "—"}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-sm font-medium text-slate-600">Concepto</dt>
            <dd className="mt-1 text-sm text-slate-900">{pago.concepto}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Preparador (usuario)</dt>
            <dd className="mt-1 text-sm text-slate-900">{pago.preparador.usuario ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Preparador (cargo)</dt>
            <dd className="mt-1 text-sm text-slate-900">{pago.preparador.cargo ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Preparador (funcionario)</dt>
            <dd className="mt-1 text-sm text-slate-900">{pago.preparador.funcionario ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Enviado por</dt>
            <dd className="mt-1 text-sm text-slate-900">{pago.enviado_por ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Enviado en</dt>
            <dd className="mt-1 text-sm text-slate-900">
              {pago.enviado_en ? formatearInstante(pago.enviado_en) : "—"}
            </dd>
          </div>
          {pago.huella && (
            <div className="sm:col-span-2">
              <dt className="text-sm font-medium text-slate-600">Huella</dt>
              <dd className="mt-1 text-sm text-slate-900">{pago.huella}</dd>
            </div>
          )}
        </dl>
      </section>

      <RetencionesPago pagoId={pago.id} pagoEstado={pago.estado} />
      <section aria-labelledby="regla-heading" className="mt-8">
        <h2 id="regla-heading" className="text-lg font-semibold">Regla aplicada</h2>
        <div className="mt-4">
          <p className="text-sm text-slate-900">
            Política: {pago.politica.codigo} v{pago.politica.numero_version} · {pago.politica.nombre}
          </p>
          {pago.estado === "BORRADOR" ? (
            <p className="mt-2 text-sm text-slate-700">La regla se congela al enviar.</p>
          ) : regla ? (
            <>
              <div className="mt-4 text-sm text-slate-900">
                <p>
                  Banda: {regla.banda?.monto_desde ?? "—"} a{" "}
                  {regla.banda?.monto_hasta ?? "Sin tope"}
                </p>
                {(regla.banda?.requisitos ?? []).map((requisito, indice) => (
                  <p key={`${requisito.accion}-${requisito.materia}-${indice}`}>
                    {requisito.accion} × {requisito.materia} × {requisito.cantidad}
                  </p>
                ))}
                <p>Aprobaciones exigidas: {regla.aprobaciones_requeridas ?? "—"}</p>
                <p>Control de duplicado: {regla.control_duplicado ?? "—"}</p>
                <p>Pago parcial: {regla.permite_pago_parcial ? "Sí" : "No"}</p>
                <p>Autorizador firmante: {regla.autorizador_firmante ? "Sí" : "No"}</p>
              </div>
              <p className="mt-3 text-sm text-slate-700">
                La regla quedó congelada al enviar el pago: un cambio posterior de la política no la modifica.
              </p>
            </>
          ) : (
            <p className="mt-2 text-sm text-slate-700">Sin regla congelada</p>
          )}
        </div>
      </section>

      <section aria-labelledby="autorizaciones-heading" className="mt-8">
        <h2 id="autorizaciones-heading" className="text-lg font-semibold">Autorizaciones</h2>
        <p className="mt-4 text-sm text-slate-900">
          {aprobacionesRealizadas} de {pago.aprobaciones_requeridas ?? "—"}
        </p>
        {pago.aprobaciones.length === 0 ? (
          <p className="mt-2 text-sm text-slate-600">Sin aprobaciones</p>
        ) : (
          <div
            className="mt-4 overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de autorizaciones del pago"
          >
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                    Actor
                  </th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                    Cargo
                  </th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                    Unidad
                  </th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                    Funcionario
                  </th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                    Requisito
                  </th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                    Decisión
                  </th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                    Motivo
                  </th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                    Fecha
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {pago.aprobaciones.map((aprobacion: AprobacionPago, index: number) => (
                  <tr key={`${aprobacion.actor}-${aprobacion.fecha}-${index}`}>
                    <td className="px-3 py-2 text-sm">{aprobacion.actor ?? "—"}</td>
                    <td className="px-3 py-2 text-sm">{aprobacion.cargo}</td>
                    <td className="px-3 py-2 text-sm">{aprobacion.unidad ?? "—"}</td>
                    <td className="px-3 py-2 text-sm">{aprobacion.funcionario ?? "—"}</td>
                    <td className="px-3 py-2 text-sm">
                      {aprobacion.requisito
                        ? `${aprobacion.requisito.accion} × ${aprobacion.requisito.materia}`
                        : "—"}
                    </td>
                    <td className="px-3 py-2 text-sm">{aprobacion.decision}</td>
                    <td className="px-3 py-2 text-sm">{aprobacion.motivo ?? "—"}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-sm">
                      {formatearInstante(aprobacion.fecha)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {pago.controles && (
        <section aria-labelledby="controles-heading" className="mt-8">
          <h2 id="controles-heading" className="text-lg font-semibold">Controles</h2>
          <ul className="mt-4 space-y-2">
            {pago.controles.controles.map((control: ControlPago) => (
              <li key={control.codigo} className="text-sm">
                {control.codigo} · {estadoControl(control)} · {control.mensaje}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section aria-labelledby="documentos-heading" className="mt-8">
        <h2 id="documentos-heading" className="text-lg font-semibold">Documentos</h2>
        {pago.documentos.length === 0 ? (
          <p className="mt-4 text-sm text-slate-600">Sin documentos vinculados</p>
        ) : (
          <div
            className="mt-4 overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de documentos del pago"
          >
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                    Etapa
                  </th>
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
                {pago.documentos.map((documento) => (
                  <tr key={`${documento.document_id}-${documento.etapa}`}>
                    <td className="whitespace-nowrap px-3 py-2 text-sm">
                      {ETAPAS_DOCUMENTO_PAGO[documento.etapa]}
                    </td>
                    <td className="px-3 py-2 text-sm">{documento.titulo}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-sm">
                      {documento.tipo ?? "—"}
                    </td>
                    <td
                      className="whitespace-nowrap px-3 py-2 text-sm"
                      title={documento.sha256 ?? ""}
                    >
                      {documento.sha256 ? `${documento.sha256.slice(0, 12)}…` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="historia-heading" className="mt-8">
        <h2 id="historia-heading" className="text-lg font-semibold">Historia</h2>
        {pago.historia.length === 0 ? (
          <p className="mt-4 text-sm text-slate-600">Sin eventos</p>
        ) : (
          <div
            className="mt-4 overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de eventos del pago"
          >
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                    Evento
                  </th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                    Actor
                  </th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                    Fecha
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {pago.historia.map((evento, index) => (
                  <tr key={`${evento.evento}-${evento.fecha}-${evento.actor}-${index}`}>
                    <td className="whitespace-nowrap px-3 py-2 text-sm">{evento.evento}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-sm">{evento.actor ?? "—"}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-sm">
                      {formatearInstante(evento.fecha)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="que-sigue-heading" className="mt-8">
        <h2 id="que-sigue-heading" className="text-lg font-semibold">Qué sigue</h2>
        <p className="mt-3 text-sm text-slate-700">
          Retenciones: {pago.fronteras.retenciones} · Conciliación: {pago.fronteras.conciliacion} · Reverso de un pago ejecutado: {pago.fronteras.reverso} · Contabilidad: {pago.fronteras.contabilidad}
        </p>
        <p className="mt-2 text-sm text-slate-700">
          KONTROL registra el pago ejecutado por la Tesorería; no lo envía al banco.
        </p>
        {pago.estado === "REGISTRADO" && (
          <p className="mt-2 text-sm text-slate-700">
            El reverso de un pago ejecutado corresponde a TRE-07.
          </p>
        )}
      </section>

      <ConfirmationDialog
        open={dialogoAbierto === "enviar"}
        title="Enviar a autorización"
        description="El pago quedará pendiente de autorización y la regla se congelará."
        confirmLabel="Enviar"
        onConfirm={() => confirmarEnviar(false, "")}
        onCancel={cerrarDialogo}
      >
        {(pago.controles?.controles ?? []).some((c) => c.codigo === "PREPARADOR" && !c.cumplido) && (
          <FormField label="Cargo preparador" htmlFor="pago-enviar-cargo">
            <select
              id="pago-enviar-cargo"
              value={cargoId}
              onChange={(event) => setCargoId(event.target.value)}
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
        )}
      </ConfirmationDialog>

      <ConfirmationDialog
        open={dialogoAbierto === "descartar"}
        title="Descartar borrador"
        description="Se descartará el borrador del pago. Esta acción no se puede deshacer."
        confirmLabel="Descartar"
        danger
        onConfirm={confirmarDescartar}
        onCancel={cerrarDialogo}
      />

      <ConfirmationDialog
        open={dialogoAbierto === "aprobar"}
        title="Aprobar pago"
        description="Confirme la aprobación del pago según la regla congelada."
        confirmLabel="Aprobar"
        onConfirm={confirmarAprobar}
        onCancel={cerrarDialogo}
      >
        <FormField label="Cargo que autoriza" htmlFor="pago-aprobar-cargo">
          <select
            id="pago-aprobar-cargo"
            value={cargoId}
            onChange={(event) => {
              setCargoId(event.target.value);
              setErrorCargo(false);
            }}
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
        {errorCargo && (
          <div role="alert" className="mt-2 text-sm text-red-700">
            Debe seleccionar el cargo
          </div>
        )}
        <FormField label="Requisito" htmlFor="pago-aprobar-requisito">
          <select
            id="pago-aprobar-requisito"
            value={requisitoIndice}
            onChange={(event) => setRequisitoIndice(event.target.value)}
            className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">Seleccione un requisito</option>
            {requisitosPendientes.map((requisito) => (
              <option key={requisito.indice} value={requisito.indice}>
                {requisito.accion} × {requisito.materia} (faltan {requisito.cantidad})
              </option>
            ))}
          </select>
        </FormField>
      </ConfirmationDialog>

      <ConfirmationDialog
        open={dialogoAbierto === "rechazar"}
        title="Rechazar pago"
        description="El pago se rechazará y no podrá registrarse."
        confirmLabel="Rechazar"
        danger
        onConfirm={confirmarRechazar}
        onCancel={cerrarDialogo}
      >
        <FormField label="Cargo que rechaza" htmlFor="pago-rechazar-cargo">
          <select
            id="pago-rechazar-cargo"
            value={cargoId}
            onChange={(event) => {
              setCargoId(event.target.value);
              setErrorCargo(false);
            }}
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
        {errorCargo && (
          <div role="alert" className="mt-2 text-sm text-red-700">
            Debe seleccionar el cargo
          </div>
        )}
        <FormField label="Motivo del rechazo" htmlFor="pago-rechazo-motivo">
          <textarea
            id="pago-rechazo-motivo"
            value={motivo}
            onChange={(event) => {
              setMotivo(event.target.value);
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
      </ConfirmationDialog>

      <ConfirmationDialog
        open={dialogoAbierto === "registrar"}
        title="Registrar pago ejecutado"
        description="Registre aquí un pago que la Tesorería ya ejecutó por el medio indicado."
        confirmLabel="Registrar"
        onConfirm={confirmarRegistrar}
        onCancel={cerrarDialogo}
      >
        <FormField label="Fecha valor" htmlFor="pago-registrar-fecha-valor">
          <input
            id="pago-registrar-fecha-valor"
            type="date"
            value={fechaValor}
            onChange={(event) => {
              setFechaValor(event.target.value);
              setErrorFechaValor(false);
            }}
            className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </FormField>
        {errorFechaValor && (
          <div role="alert" className="mt-2 text-sm text-red-700">
            Debe indicar la fecha valor
          </div>
        )}
        <FormField
          label="Referencia externa"
          htmlFor="pago-registrar-referencia"
          help={pago.medio.patron_referencia ? `Patrón: ${pago.medio.patron_referencia}` : undefined}
        >
          <input
            id="pago-registrar-referencia"
            type="text"
            value={referenciaExterna}
            onChange={(event) => {
              setReferenciaExterna(event.target.value);
              setErrorReferencia(false);
            }}
            className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </FormField>
        {errorReferencia && (
          <div role="alert" className="mt-2 text-sm text-red-700">
            La referencia externa es obligatoria para este medio
          </div>
        )}
      </ConfirmationDialog>

      <ConfirmationDialog
        open={dialogoAbierto === "anular"}
        title="Anular antes de ejecutar"
        description="El pago se anulará antes de ser ejecutado."
        confirmLabel="Anular"
        danger
        onConfirm={confirmarAnular}
        onCancel={cerrarDialogo}
      >
        <FormField label="Motivo de la anulación" htmlFor="pago-anular-motivo">
          <textarea
            id="pago-anular-motivo"
            value={motivo}
            onChange={(event) => {
              setMotivo(event.target.value);
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
      </ConfirmationDialog>

      <ConfirmationDialog
        open={dialogoAbierto === "duplicado"}
        title="Confirmar envío con duplicado"
        description="El sistema detectó un posible pago duplicado. Debe proporcionar un motivo para confirmar el envío."
        confirmLabel="Confirmar envío"
        danger
        onConfirm={confirmarDuplicado}
        onCancel={() => {
          setDialogoAbierto("enviar");
          setMotivo("");
          setErrorMotivo(false);
        }}
      >
        <FormField label="Motivo de la confirmación" htmlFor="pago-duplicado-motivo">
          <textarea
            id="pago-duplicado-motivo"
            value={motivo}
            onChange={(event) => {
              setMotivo(event.target.value);
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
      </ConfirmationDialog>
    </PageContent>
  );
}
