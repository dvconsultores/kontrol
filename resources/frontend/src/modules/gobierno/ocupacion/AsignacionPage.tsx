import { useState } from "react";
import { Link, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import { LoadingState } from "@/components/LoadingState";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { formatearFecha } from "@/i18n";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_OCUPACION,
  esDelegacion,
  ETIQUETAS_ESTADO_ASIGNACION,
  ETIQUETAS_HISTORIA_OCUPACION,
  ETIQUETAS_SITUACION_ASIGNACION,
} from "@/modules/gobierno/api";
import type {
  AsignacionDetalle,
  OpcionesOcupacion,
  CompetenciaOcupacion,
  HistoriaOcupacion,
} from "@/modules/gobierno/api";

type Panel = "descartar" | "revocar" | "finalizar" | "avocar" | null;

export function AsignacionPage() {
  const { asignacionId } = useParams<{ asignacionId: string }>();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const puedeVer = tiene("gobierno_ocupacion:view", "empresa");
  const puedeGestionar = tiene("gobierno_ocupacion:manage", "empresa");
  const puedeActivar = tiene("gobierno_ocupacion:activate", "empresa");
  const puedeRevocar = tiene("gobierno_ocupacion:revoke", "empresa");

  const claveDetalle = [
    ...CONSULTA_OCUPACION,
    activeCompanyId,
    "asignacion",
    asignacionId,
  ];

  const consultaDetalle = useQuery({
    queryKey: claveDetalle,
    queryFn: () =>
      apiFetch<AsignacionDetalle>(
        `/gobierno/ocupacion/asignaciones/${asignacionId}`,
      ),
    enabled: puedeVer && Boolean(activeCompanyId) && Boolean(asignacionId),
    retry: false,
  });

  const detalle = consultaDetalle.data;

  const consultaOpciones = useQuery({
    queryKey: [...CONSULTA_OCUPACION, activeCompanyId, "opciones", detalle?.cargo.ejercicio],
    queryFn: () =>
      apiFetch<OpcionesOcupacion>(
        `/gobierno/ocupacion/opciones?ejercicio=${detalle?.cargo.ejercicio}`,
      ),
    enabled: puedeRevocar && Boolean(detalle?.cargo.ejercicio),
    retry: false,
  });

  const [panel, setPanel] = useState<Panel>(null);
  const [enviando, setEnviando] = useState(false);

  const [motivoDescartar, setMotivoDescartar] = useState("");
  const [actoRevocacionId, setActoRevocacionId] = useState("");
  const [fechaRevocacion, setFechaRevocacion] = useState("");
  const [motivoRevocacion, setMotivoRevocacion] = useState("");
  const [fechaFinalizacion, setFechaFinalizacion] = useState("");
  const [motivoFinalizacion, setMotivoFinalizacion] = useState("");
  const [actoAvocacionId, setActoAvocacionId] = useState("");
  const [asuntoAvocacion, setAsuntoAvocacion] = useState("");

  const [erroresServidor, setErroresServidor] = useState<Record<string, string[]>>({});
  const [alertaCambio, setAlertaCambio] = useState<string | null>(null);

  const recargar = () => {
    void queryClient.invalidateQueries({ queryKey: [...CONSULTA_OCUPACION] });
  };

  if (!puedeVer) {
    return (
      <PageContent>
        <EmptyState title="Sin acceso" description="No tiene permiso para ver esta sección." />
      </PageContent>
    );
  }

  if (!activeCompanyId || !asignacionId) {
    return (
      <PageContent>
        <EmptyState title="Sin datos" description="Faltan datos para cargar la asignación." />
      </PageContent>
    );
  }

  if (consultaDetalle.isLoading) {
    return (
      <PageContent>
        <LoadingState />
      </PageContent>
    );
  }

  if (consultaDetalle.isError) {
    const e = consultaDetalle.error;
    if (e instanceof ApiError && e.status === 404) {
      return (
        <PageContent>
          <PageHeader
            crumbs={[
              { label: "Gobierno" },
              { label: "Ocupación de cargos", to: "/gobierno/ocupacion" },
              { label: "Asignaciones", to: "/gobierno/ocupacion/asignaciones" },
            ]}
            title="Asignación no encontrada"
          />
          <EmptyState title="Asignación no encontrada" description="La asignación solicitada no existe." />
        </PageContent>
      );
    }
    return (
      <PageContent>
        <PageHeader
          crumbs={[
            { label: "Gobierno" },
            { label: "Ocupación de cargos", to: "/gobierno/ocupacion" },
            { label: "Asignaciones", to: "/gobierno/ocupacion/asignaciones" },
          ]}
          title="Error"
        />
        <ErrorDeCarga message="No fue posible cargar la asignación." onRetry={consultaDetalle.refetch} />
      </PageContent>
    );
  }

  if (!detalle) {
    return (
      <PageContent>
        <EmptyState title="Sin datos" description="No hay datos de la asignación." />
      </PageContent>
    );
  }

  const manejarError = (e: unknown) => {
    if (e instanceof ApiError) {
      if (e.status === 409 && e.code === "GOV_ASSIGNMENT_STALE") {
        setAlertaCambio("Otra persona cambió esta asignación. Recargue la página.");
        recargar();
        return;
      }
      if (e.status === 409 && e.code === "GOV_SOD_CONFLICT") {
        setAlertaCambio(e.message);
        return;
      }
      if (e.status === 403 && e.code === "GOV_ASSIGNMENT_SELF_ACTIVATION") {
        setAlertaCambio("Quien registró la asignación no puede activarla.");
        return;
      }
      if (e.status === 422 && e.code === "VALIDATION_ERROR") {
        setErroresServidor(e.fieldErrors);
        const errorGeneral = e.fieldErrors["_"]?.[0];
        if (errorGeneral) {
          setAlertaCambio(errorGeneral);
        }
        return;
      }
      if (e.status >= 400 && e.status < 500) {
        setAlertaCambio(e.message);
        return;
      }
      notify({ type: "error", title: "No fue posible completar la acción" });
      return;
    }
    notify({ type: "error", title: "No fue posible completar la acción" });
  };

  const escribirDetalle = async (
    ruta: string,
    method: "POST",
    body: Record<string, unknown>,
  ) => {
    try {
      const nuevoDetalle = await apiFetch<AsignacionDetalle>(ruta, {
        method,
        body,
        ifMatch: String(detalle.version),
      });
      queryClient.setQueryData(claveDetalle, nuevoDetalle);
      void queryClient.invalidateQueries({ queryKey: [...CONSULTA_OCUPACION] });
      setErroresServidor({});
      setAlertaCambio(null);
      return nuevoDetalle;
    } catch (e) {
      manejarError(e);
      throw e;
    }
  };

  const cerrarPanel = () => {
    setPanel(null);
    setMotivoDescartar("");
    setActoRevocacionId("");
    setFechaRevocacion("");
    setMotivoRevocacion("");
    setFechaFinalizacion("");
    setMotivoFinalizacion("");
    setActoAvocacionId("");
    setAsuntoAvocacion("");
    setErroresServidor({});
    setAlertaCambio(null);
  };

  const descartar = async () => {
    if (enviando) return;
    setEnviando(true);
    try {
      await escribirDetalle(
        `/gobierno/ocupacion/asignaciones/${detalle.id}/descartar`,
        "POST",
        { motivo: motivoDescartar },
      );
      cerrarPanel();
      notify({ type: "success", title: "Asignación descartada" });
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const activar = async () => {
    if (enviando) return;
    setEnviando(true);
    try {
      await escribirDetalle(
        `/gobierno/ocupacion/asignaciones/${detalle.id}/activar`,
        "POST",
        {},
      );
      cerrarPanel();
      notify({ type: "success", title: "Asignación activada" });
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const revocar = async () => {
    if (enviando) return;
    setEnviando(true);
    try {
      await escribirDetalle(
        `/gobierno/ocupacion/asignaciones/${detalle.id}/revocar`,
        "POST",
        {
          acto_id: actoRevocacionId,
          fecha: fechaRevocacion,
          motivo: motivoRevocacion,
        },
      );
      cerrarPanel();
      notify({ type: "success", title: "Asignación revocada" });
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const finalizar = async () => {
    if (enviando) return;
    setEnviando(true);
    try {
      await escribirDetalle(
        `/gobierno/ocupacion/asignaciones/${detalle.id}/finalizar`,
        "POST",
        { fecha: fechaFinalizacion, motivo: motivoFinalizacion },
      );
      cerrarPanel();
      notify({ type: "success", title: "Asignación finalizada" });
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const avocar = async () => {
    if (enviando) return;
    setEnviando(true);
    try {
      await escribirDetalle(
        `/gobierno/ocupacion/asignaciones/${detalle.id}/avocar`,
        "POST",
        { acto_id: actoAvocacionId, asunto: asuntoAvocacion },
      );
      cerrarPanel();
      notify({ type: "success", title: "Avocación registrada" });
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const esMotivoDescartarValido =
    motivoDescartar.trim().length >= 10 && motivoDescartar.length <= 500;
  const esMotivoRevocacionValido =
    motivoRevocacion.trim().length >= 10 && motivoRevocacion.length <= 500;
  const esMotivoFinalizacionValido =
    motivoFinalizacion.trim().length >= 10 && motivoFinalizacion.length <= 500;
  const esAsuntoAvocacionValido =
    asuntoAvocacion.trim().length >= 10 && asuntoAvocacion.length <= 500;

  const panelRender =
    panel === "descartar" ? (
      <section aria-labelledby="descartar-asignacion-titulo" className="mb-8 rounded-lg border border-border-subtle p-4">
        <h2 id="descartar-asignacion-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Descartar asignación
        </h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (esMotivoDescartarValido) {
              void descartar();
            }
          }}
          className="space-y-4"
        >
          <FormField label="Motivo" htmlFor="motivo-descartar">
            <TextInput
              id="motivo-descartar"
              value={motivoDescartar}
              onChange={(e) => setMotivoDescartar(e.target.value)}
              placeholder="Escriba el motivo (10 a 500 caracteres)"
              className="w-full"
            />
            {erroresServidor["motivo"] ? (
              <p className="mt-1 text-sm text-danger-600" role="alert">
                {erroresServidor["motivo"].join(", ")}
              </p>
            ) : null}
          </FormField>
          {alertaCambio ? (
            <p className="text-sm text-danger-600" role="alert">
              {alertaCambio}
            </p>
          ) : null}
          <div className="flex gap-2">
            <Button type="submit" variant="primary" disabled={!esMotivoDescartarValido || enviando}>
              Descartar
            </Button>
            <Button type="button" variant="ghost" onClick={cerrarPanel}>
              Cancelar
            </Button>
          </div>
        </form>
      </section>
    ) : panel === "revocar" ? (
      <section aria-labelledby="revocar-asignacion-titulo" className="mb-8 rounded-lg border border-border-subtle p-4">
        <h2 id="revocar-asignacion-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Revocar asignación
        </h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (actoRevocacionId && fechaRevocacion && esMotivoRevocacionValido) {
              void revocar();
            }
          }}
          className="space-y-4"
        >
          <FormField label="Acto de revocación" htmlFor="acto-revocacion">
            <select
              id="acto-revocacion"
              className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900 focus:border-brand-500 focus:outline-none"
              value={actoRevocacionId}
              onChange={(e) => setActoRevocacionId(e.target.value)}
            >
              <option value="">Seleccione un acto</option>
              {consultaOpciones.data?.actos?.map((acto) => (
                <option key={acto.id} value={acto.id}>
                  {acto.tipo} {acto.numero} · {acto.emisor_cargo}
                </option>
              ))}
            </select>
            {erroresServidor["acto_id"] ? (
              <p className="mt-1 text-sm text-danger-600" role="alert">
                {erroresServidor["acto_id"].join(", ")}
              </p>
            ) : null}
          </FormField>
          <FormField label="Fecha" htmlFor="fecha-revocacion">
            <input
              type="date"
              id="fecha-revocacion"
              className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900 focus:border-brand-500 focus:outline-none"
              value={fechaRevocacion}
              onChange={(e) => setFechaRevocacion(e.target.value)}
            />
            {erroresServidor["fecha"] ? (
              <p className="mt-1 text-sm text-danger-600" role="alert">
                {erroresServidor["fecha"].join(", ")}
              </p>
            ) : null}
          </FormField>
          <FormField label="Motivo" htmlFor="motivo-revocacion">
            <TextInput
              id="motivo-revocacion"
              value={motivoRevocacion}
              onChange={(e) => setMotivoRevocacion(e.target.value)}
              placeholder="Escriba el motivo (10 a 500 caracteres)"
              className="w-full"
            />
            {erroresServidor["motivo"] ? (
              <p className="mt-1 text-sm text-danger-600" role="alert">
                {erroresServidor["motivo"].join(", ")}
              </p>
            ) : null}
          </FormField>
          {alertaCambio ? (
            <p className="text-sm text-danger-600" role="alert">
              {alertaCambio}
            </p>
          ) : null}
          <div className="flex gap-2">
            <Button
              type="submit"
              variant="primary"
              disabled={!actoRevocacionId || !fechaRevocacion || !esMotivoRevocacionValido || enviando}
            >
              Revocar
            </Button>
            <Button type="button" variant="ghost" onClick={cerrarPanel}>
              Cancelar
            </Button>
          </div>
        </form>
      </section>
    ) : panel === "finalizar" ? (
      <section aria-labelledby="finalizar-asignacion-titulo" className="mb-8 rounded-lg border border-border-subtle p-4">
        <h2 id="finalizar-asignacion-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Finalizar asignación
        </h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (fechaFinalizacion && esMotivoFinalizacionValido) {
              void finalizar();
            }
          }}
          className="space-y-4"
        >
          <FormField label="Fecha" htmlFor="fecha-finalizacion">
            <input
              type="date"
              id="fecha-finalizacion"
              className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900 focus:border-brand-500 focus:outline-none"
              value={fechaFinalizacion}
              onChange={(e) => setFechaFinalizacion(e.target.value)}
            />
            {erroresServidor["fecha"] ? (
              <p className="mt-1 text-sm text-danger-600" role="alert">
                {erroresServidor["fecha"].join(", ")}
              </p>
            ) : null}
          </FormField>
          <FormField label="Motivo" htmlFor="motivo-finalizacion">
            <TextInput
              id="motivo-finalizacion"
              value={motivoFinalizacion}
              onChange={(e) => setMotivoFinalizacion(e.target.value)}
              placeholder="Escriba el motivo (10 a 500 caracteres)"
              className="w-full"
            />
            {erroresServidor["motivo"] ? (
              <p className="mt-1 text-sm text-danger-600" role="alert">
                {erroresServidor["motivo"].join(", ")}
              </p>
            ) : null}
          </FormField>
          {alertaCambio ? (
            <p className="text-sm text-danger-600" role="alert">
              {alertaCambio}
            </p>
          ) : null}
          <div className="flex gap-2">
            <Button
              type="submit"
              variant="primary"
              disabled={!fechaFinalizacion || !esMotivoFinalizacionValido || enviando}
            >
              Finalizar
            </Button>
            <Button type="button" variant="ghost" onClick={cerrarPanel}>
              Cancelar
            </Button>
          </div>
        </form>
      </section>
    ) : panel === "avocar" ? (
      <section aria-labelledby="avocar-asignacion-titulo" className="mb-8 rounded-lg border border-border-subtle p-4">
        <h2 id="avocar-asignacion-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Avocar competencias
        </h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (actoAvocacionId && esAsuntoAvocacionValido) {
              void avocar();
            }
          }}
          className="space-y-4"
        >
          <FormField label="Acto" htmlFor="acto-avocacion">
            <select
              id="acto-avocacion"
              className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900 focus:border-brand-500 focus:outline-none"
              value={actoAvocacionId}
              onChange={(e) => setActoAvocacionId(e.target.value)}
            >
              <option value="">Seleccione un acto</option>
              {consultaOpciones.data?.actos?.map((acto) => (
                <option key={acto.id} value={acto.id}>
                  {acto.tipo} {acto.numero} · {acto.emisor_cargo}
                </option>
              ))}
            </select>
            {erroresServidor["acto_id"] ? (
              <p className="mt-1 text-sm text-danger-600" role="alert">
                {erroresServidor["acto_id"].join(", ")}
              </p>
            ) : null}
          </FormField>
          <FormField label="Asunto" htmlFor="asunto-avocacion">
            <TextInput
              id="asunto-avocacion"
              value={asuntoAvocacion}
              onChange={(e) => setAsuntoAvocacion(e.target.value)}
              placeholder="Escriba el asunto (10 a 500 caracteres)"
              className="w-full"
            />
            {erroresServidor["asunto"] ? (
              <p className="mt-1 text-sm text-danger-600" role="alert">
                {erroresServidor["asunto"].join(", ")}
              </p>
            ) : null}
          </FormField>
          {alertaCambio ? (
            <p className="text-sm text-danger-600" role="alert">
              {alertaCambio}
            </p>
          ) : null}
          <div className="flex gap-2">
            <Button
              type="submit"
              variant="primary"
              disabled={!actoAvocacionId || !esAsuntoAvocacionValido || enviando}
            >
              Avocar
            </Button>
            <Button type="button" variant="ghost" onClick={cerrarPanel}>
              Cancelar
            </Button>
          </div>
        </form>
      </section>
    ) : null;

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Ocupación de cargos", to: "/gobierno/ocupacion" },
          { label: "Asignaciones", to: "/gobierno/ocupacion/asignaciones" },
          { label: detalle.codigo },
        ]}
        title={`${detalle.figura_etiqueta} · ${detalle.funcionario.nombre}`}
        description={`${detalle.cargo.nombre} · ${detalle.cargo.unidad}`}
      />

      {alertaCambio ? (
        <p className="mb-4 text-sm text-danger-600" role="alert">
          {alertaCambio}
        </p>
      ) : null}

      <div className="mb-8 flex flex-wrap items-center gap-2">
        {detalle.status === "BORRADOR" && puedeGestionar ? (
          <Link
            to={`/gobierno/ocupacion/asignaciones/${detalle.id}/editar`}
            className="inline-flex items-center rounded-md border border-border-subtle bg-white px-3 py-2 text-sm font-medium text-text-900 hover:bg-surface-50"
          >
            Editar
          </Link>
        ) : null}
        {detalle.status === "BORRADOR" && puedeGestionar ? (
          <Button variant="secondary" onClick={() => setPanel("descartar")}>
            Descartar
          </Button>
        ) : null}
        {detalle.status === "BORRADOR" && puedeActivar ? (
          <div className="w-full sm:w-auto">
            <AsyncButton variant="primary" disabled={enviando} onClick={activar}>
              Activar
            </AsyncButton>
            <p className="mt-1 text-xs text-text-500">
              La activa una persona distinta de quien la registró.
            </p>
          </div>
        ) : null}
        {detalle.status === "ACTIVO" && puedeRevocar ? (
          <Button variant="secondary" onClick={() => setPanel("revocar")}>
            Revocar
          </Button>
        ) : null}
        {detalle.status === "ACTIVO" && puedeRevocar ? (
          <Button variant="secondary" onClick={() => setPanel("finalizar")}>
            Finalizar
          </Button>
        ) : null}
        {detalle.status === "ACTIVO" && esDelegacion(detalle.figura) && puedeRevocar ? (
          <Button variant="secondary" onClick={() => setPanel("avocar")}>
            Avocar
          </Button>
        ) : null}
      </div>

      {panelRender}

      <section aria-labelledby="quien-que-cargo" className="mb-8">
        <h2 id="quien-que-cargo" className="mb-4 text-lg font-semibold text-text-900">
          Quién y qué cargo
        </h2>
        <dl className="grid gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-text-700">Funcionario</dt>
            <dd className="mt-1 text-text-900">
              <Link
                to={`/gobierno/ocupacion/funcionarios/${detalle.funcionario.id}`}
                className="font-medium text-brand-700 underline"
              >
                {detalle.funcionario.nombre}
              </Link>
              <span className="block text-sm text-text-500">
                {detalle.funcionario.documento}
              </span>
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Cargo</dt>
            <dd className="mt-1 text-text-900">
              <Link
                to={`/gobierno/ocupacion/cargos/${detalle.cargo.id}`}
                className="font-medium text-brand-700 underline"
              >
                {detalle.cargo.nombre}
              </Link>
            </dd>
          </div>
          {detalle.cargo_origen ? (
            <div>
              <dt className="text-sm font-medium text-text-700">Cargo de origen</dt>
              <dd className="mt-1 text-text-900">{detalle.cargo_origen.nombre}</dd>
            </div>
          ) : null}
          <div>
            <dt className="text-sm font-medium text-text-700">Figura</dt>
            <dd className="mt-1 text-text-900">{detalle.figura_etiqueta}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Situación</dt>
            <dd className="mt-1 text-text-900">
              {ETIQUETAS_SITUACION_ASIGNACION[detalle.situacion] ?? detalle.situacion}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Estado</dt>
            <dd className="mt-1 text-text-900">
              {ETIQUETAS_ESTADO_ASIGNACION[detalle.status] ?? detalle.status}
            </dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="vigencia-asignacion" className="mb-8">
        <h2 id="vigencia-asignacion" className="mb-4 text-lg font-semibold text-text-900">
          Vigencia
        </h2>
        <dl className="grid gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-text-700">Desde</dt>
            <dd className="mt-1 text-text-900">
              {detalle.desde ? formatearFechaDeNegocio(detalle.desde) : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Hasta</dt>
            <dd className="mt-1 text-text-900">
              {detalle.hasta ? formatearFechaDeNegocio(detalle.hasta) : "sin fecha final"}
            </dd>
          </div>
          {detalle.fin_efectivo ? (
            <div>
              <dt className="text-sm font-medium text-text-700">Fin efectivo</dt>
              <dd className="mt-1 text-text-900">
                {formatearFechaDeNegocio(detalle.fin_efectivo)}
              </dd>
            </div>
          ) : null}
          {detalle.ejerce ? (
            <div className="sm:col-span-2">
              <dt className="text-sm font-medium text-text-700">Ejercicio</dt>
              <dd className="mt-1 text-text-900">Ejerce el cargo hoy</dd>
            </div>
          ) : null}
        </dl>
      </section>

      <section aria-labelledby="acto-base-juridica" className="mb-8">
        <h2 id="acto-base-juridica" className="mb-4 text-lg font-semibold text-text-900">
          Acto y base jurídica
        </h2>
        <dl className="grid gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-text-700">Acto</dt>
            <dd className="mt-1 text-text-900">
              <Link
                to={`/gobierno/actos/${detalle.acto.id}`}
                className="font-medium text-brand-700 underline"
              >
                {detalle.acto.tipo} {detalle.acto.numero}
              </Link>
              <span className="block text-sm text-text-500">
                {detalle.acto.fecha ? formatearFechaDeNegocio(detalle.acto.fecha) : "—"}
                {detalle.acto.medio ? ` · ${detalle.acto.medio}` : ""}
                {detalle.acto.emisor_cargo ? ` · ${detalle.acto.emisor_cargo}` : ""}
              </span>
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Fundamento</dt>
            <dd className="mt-1 text-text-900">{detalle.fundamento || "—"}</dd>
          </div>
          {detalle.rendicion ? (
            <div>
              <dt className="text-sm font-medium text-text-700">Rendición</dt>
              <dd className="mt-1 text-text-900">{detalle.rendicion}</dd>
            </div>
          ) : null}
          {detalle.autorizacion_concejo ? (
            <div>
              <dt className="text-sm font-medium text-text-700">Autorización del concejo</dt>
              <dd className="mt-1 text-text-900">{detalle.autorizacion_concejo}</dd>
            </div>
          ) : null}
          {detalle.maxima_autoridad ? (
            <div>
              <dt className="text-sm font-medium text-text-700">Máxima autoridad</dt>
              <dd className="mt-1 text-text-900">Sí</dd>
            </div>
          ) : null}
          {detalle.acto_revocacion ? (
            <div>
              <dt className="text-sm font-medium text-text-700">Acto de revocación</dt>
              <dd className="mt-1 text-text-900">
                {detalle.acto_revocacion.tipo} {detalle.acto_revocacion.numero}
              </dd>
            </div>
          ) : null}
          {detalle.motivo_fin ? (
            <div>
              <dt className="text-sm font-medium text-text-700">Motivo de fin</dt>
              <dd className="mt-1 text-text-900">{detalle.motivo_fin}</dd>
            </div>
          ) : null}
        </dl>
      </section>

      {detalle.competencias.length > 0 ? (
        <section aria-labelledby="competencias-delegadas" className="mb-8">
          <h2 id="competencias-delegadas" className="mb-4 text-lg font-semibold text-text-900">
            Competencias delegadas
          </h2>
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de competencias delegadas"
          >
            <table className="w-full border-collapse text-left">
              <caption className="sr-only">Competencias delegadas</caption>
              <thead>
                <tr className="border-b border-border-subtle">
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    Acción
                  </th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    Materia
                  </th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    Límite
                  </th>
                </tr>
              </thead>
              <tbody>
                {detalle.competencias.map((c: CompetenciaOcupacion) => (
                  <tr key={`${c.accion}-${c.materia}`} className="border-b border-border-subtle">
                    <td className="px-3 py-2 text-sm text-text-900">{c.accion}</td>
                    <td className="px-3 py-2 text-sm text-text-900">{c.materia}</td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {c.tipo_limite === "SIN_LIMITE"
                        ? "Sin límite"
                        : `${c.monto ?? ""} ${c.moneda ?? ""}`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <section aria-labelledby="autoridad-ejerce" className="mb-8">
        <h2 id="autoridad-ejerce" className="mb-4 text-lg font-semibold text-text-900">
          Autoridad que ejerce
        </h2>
        {detalle.autoridad.length === 0 ? (
          <p className="text-sm text-text-700">No ejerce autoridad a esta fecha.</p>
        ) : (
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de autoridad que ejerce"
          >
            <table className="w-full border-collapse text-left">
              <caption className="sr-only">Autoridad que ejerce</caption>
              <thead>
                <tr className="border-b border-border-subtle">
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    Acción
                  </th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    Materia
                  </th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    Límite
                  </th>
                </tr>
              </thead>
              <tbody>
                {detalle.autoridad.map((a) => (
                  <tr key={`${a.accion}-${a.materia}`} className="border-b border-border-subtle">
                    <td className="px-3 py-2 text-sm text-text-900">{a.accion}</td>
                    <td className="px-3 py-2 text-sm text-text-900">{a.materia}</td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {a.tipo_limite === "SIN_LIMITE" ? "Sin límite" : `${a.monto ?? ""} ${a.moneda ?? ""}`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {detalle.avocaciones.length > 0 ? (
        <section aria-labelledby="avocaciones-asignacion" className="mb-8">
          <h2 id="avocaciones-asignacion" className="mb-4 text-lg font-semibold text-text-900">
            Avocaciones
          </h2>
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de avocaciones"
          >
            <table className="w-full border-collapse text-left">
              <caption className="sr-only">Avocaciones</caption>
              <thead>
                <tr className="border-b border-border-subtle">
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    Asunto
                  </th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    Acto
                  </th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    Actor
                  </th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    Fecha
                  </th>
                </tr>
              </thead>
              <tbody>
                {detalle.avocaciones.map((a) => (
                  <tr key={a.id} className="border-b border-border-subtle">
                    <td className="px-3 py-2 text-sm text-text-900">{a.asunto}</td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {a.acto.tipo} {a.acto.numero}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">{a.actor}</td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {a.creado_en ? formatearFechaDeNegocio(a.creado_en) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <section aria-labelledby="historia-asignacion">
        <h2 id="historia-asignacion" className="mb-4 text-lg font-semibold text-text-900">
          Historia
        </h2>
        <div
          className="relative overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Tabla de historia de la asignación"
        >
          <table className="w-full border-collapse text-left">
            <caption className="sr-only">Historia de la asignación</caption>
            <thead>
              <tr className="border-b border-border-subtle">
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Evento
                </th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Usuario
                </th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Fecha
                </th>
              </tr>
            </thead>
            <tbody>
              {detalle.historia.map((h: HistoriaOcupacion, indice: number) => (
                <tr key={`${h.tipo}-${h.creado_en}-${indice}`} className="border-b border-border-subtle">
                  <td className="px-3 py-2 text-sm text-text-900">
                    {ETIQUETAS_HISTORIA_OCUPACION[h.tipo] ?? h.tipo}
                  </td>
                  <td className="px-3 py-2 text-sm text-text-900">
                    {h.actor ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-sm text-text-900">
                    {formatearFecha(h.creado_en)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <dl className="mt-4 grid gap-4 sm:grid-cols-3">
          <div>
            <dt className="text-sm font-medium text-text-700">Registrada por</dt>
            <dd className="mt-1 text-text-900">
              {detalle.registrada_por ?? "—"}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Activada por</dt>
            <dd className="mt-1 text-text-900">
              {detalle.activada_por ?? "—"}
              {detalle.activada_en
                ? ` · ${formatearFecha(detalle.activada_en)}`
                : ""}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Terminada por</dt>
            <dd className="mt-1 text-text-900">
              {detalle.terminada_por ?? "—"}
              {detalle.terminada_en
                ? ` · ${formatearFecha(detalle.terminada_en)}`
                : ""}
            </dd>
          </div>
        </dl>
      </section>
    </PageContent>
  );
}
