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
  CONSULTA_IDENTIDAD,
  consultaDeFecha,
  ETIQUETAS_ESTADO_VINCULO,
  ETIQUETAS_SITUACION_VINCULO,
  ETIQUETAS_CATEGORIA_SEPARACION,
  ETIQUETAS_MOTIVO_SIN_AUTORIDAD,
  ETIQUETAS_HISTORIA_VINCULO,
} from "@/modules/gobierno/api";
import type {
  VinculoDetalle,
  OcupacionInstitucional,
  HistoriaIdentidad,
} from "@/modules/gobierno/api";

type Panel = "descartar" | "cerrar" | "revocar" | null;

export function VinculoPage() {
  const { vinculoId } = useParams<{ vinculoId: string }>();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const puedeVer = tiene("gobierno_identidad:view", "empresa");
  const puedeGestionar = tiene("gobierno_identidad:manage", "empresa");
  const puedeActivar = tiene("gobierno_identidad:activate", "empresa");
  const puedeRevocar = tiene("gobierno_identidad:revoke", "empresa");

  const [fecha, setFecha] = useState("");
  const [panel, setPanel] = useState<Panel>(null);
  const [enviando, setEnviando] = useState(false);

  const [motivoDescartar, setMotivoDescartar] = useState("");
  const [fechaCierre, setFechaCierre] = useState("");
  const [motivoCierre, setMotivoCierre] = useState("");
  const [fechaRevocacion, setFechaRevocacion] = useState("");
  const [motivoRevocacion, setMotivoRevocacion] = useState("");

  const [erroresServidor, setErroresServidor] = useState<Record<string, string[]>>({});
  const [alertaCambio, setAlertaCambio] = useState<string | null>(null);

  const claveDetalle = [
    ...CONSULTA_IDENTIDAD,
    activeCompanyId,
    "vinculo",
    vinculoId,
    fecha,
  ];

  const consultaDetalle = useQuery({
    queryKey: claveDetalle,
    queryFn: () =>
      apiFetch<VinculoDetalle>(
        `/gobierno/identidad/vinculos/${vinculoId}${consultaDeFecha(fecha)}`,
      ),
    enabled: puedeVer && Boolean(activeCompanyId) && Boolean(vinculoId),
    retry: false,
  });

  const detalle = consultaDetalle.data;

  const recargar = () => {
    void queryClient.invalidateQueries({ queryKey: [...CONSULTA_IDENTIDAD, activeCompanyId] });
  };

  const cerrarPanel = () => {
    setPanel(null);
    setMotivoDescartar("");
    setFechaCierre("");
    setMotivoCierre("");
    setFechaRevocacion("");
    setMotivoRevocacion("");
    setErroresServidor({});
    setAlertaCambio(null);
  };

  const manejarError = (e: unknown) => {
    if (e instanceof ApiError) {
      if (e.status === 409 || e.status === 412) {
        setAlertaCambio(e.message);
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
    body: Record<string, unknown>,
  ) => {
    try {
      const nuevoDetalle = await apiFetch<VinculoDetalle>(ruta, {
        method: "POST",
        body,
        ifMatch: String(detalle?.version ?? ""),
      });
      queryClient.setQueryData(claveDetalle, nuevoDetalle);
      recargar();
      setErroresServidor({});
      setAlertaCambio(null);
      return nuevoDetalle;
    } catch (e) {
      manejarError(e);
      throw e;
    }
  };

  if (!puedeVer) {
    return (
      <PageContent>
        <EmptyState title="Sin acceso" description="No tiene permiso para ver esta sección." />
      </PageContent>
    );
  }

  if (!activeCompanyId || !vinculoId) {
    return (
      <PageContent>
        <EmptyState title="Sin datos" description="Faltan datos para cargar el vínculo." />
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
              { label: "Identidad institucional", to: "/gobierno/identidad" },
            ]}
            title="Vínculo no encontrado"
          />
          <EmptyState
            title="Vínculo no encontrado"
            description="El vínculo solicitado no existe."
            action={
              <Link
                to="/gobierno/identidad"
                className="inline-flex items-center rounded-md border border-border-subtle bg-white px-3 py-2 text-sm font-medium text-text-900 hover:bg-surface-50"
              >
                Volver a Identidad institucional
              </Link>
            }
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        <ErrorDeCarga message={consultaDetalle.error.message} />
      </PageContent>
    );
  }

  if (!detalle) {
    return (
      <PageContent>
        <EmptyState title="Vínculo no encontrado" description="El vínculo solicitado no existe." />
      </PageContent>
    );
  }

  const activar = async () => {
    if (enviando) return;
    setEnviando(true);
    try {
      await escribirDetalle(
        `/gobierno/identidad/vinculos/${detalle.id}/activar`,
        {},
      );
      cerrarPanel();
      notify({ type: "success", title: "Vínculo activado" });
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const descartar = async () => {
    if (enviando) return;
    setEnviando(true);
    try {
      await escribirDetalle(
        `/gobierno/identidad/vinculos/${detalle.id}/descartar`,
        { motivo: motivoDescartar },
      );
      cerrarPanel();
      notify({ type: "success", title: "Vínculo descartado" });
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const cerrar = async () => {
    if (enviando) return;
    setEnviando(true);
    try {
      await escribirDetalle(
        `/gobierno/identidad/vinculos/${detalle.id}/cerrar`,
        { fecha: fechaCierre, motivo: motivoCierre },
      );
      cerrarPanel();
      notify({ type: "success", title: "Vínculo cerrado" });
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
        `/gobierno/identidad/vinculos/${detalle.id}/revocar`,
        { fecha: fechaRevocacion, motivo: motivoRevocacion },
      );
      cerrarPanel();
      notify({ type: "success", title: "Vínculo revocado" });
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const esMotivoValido = (motivo: string) => motivo.length >= 10 && motivo.length <= 500;

  const panelRender = panel === "descartar" ? (
    <section aria-labelledby="descartar-vinculo-titulo" className="mb-8 rounded-lg border border-border-subtle p-4">
      <h2 id="descartar-vinculo-titulo" className="mb-4 text-lg font-semibold text-text-900">
        Descartar vínculo
      </h2>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (motivoDescartar) void descartar();
        }}
        className="space-y-4"
      >
        <FormField label="Motivo" htmlFor="motivo-descartar">
          <TextInput
            id="motivo-descartar"
            value={motivoDescartar}
            onChange={(e) => setMotivoDescartar(e.target.value)}
            placeholder="Escriba el motivo del descarte"
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
          <Button type="submit" variant="primary" disabled={!motivoDescartar || enviando}>
            Descartar
          </Button>
          <Button type="button" variant="ghost" onClick={cerrarPanel}>
            Cancelar
          </Button>
        </div>
      </form>
    </section>
  ) : panel === "cerrar" ? (
    <section aria-labelledby="cerrar-vinculo-titulo" className="mb-8 rounded-lg border border-border-subtle p-4">
      <h2 id="cerrar-vinculo-titulo" className="mb-4 text-lg font-semibold text-text-900">
        Cerrar vínculo
      </h2>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (fechaCierre && esMotivoValido(motivoCierre)) void cerrar();
        }}
        className="space-y-4"
      >
        <FormField label="Fecha" htmlFor="fecha-cierre">
          <input
            type="date"
            id="fecha-cierre"
            className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900 focus:border-brand-500 focus:outline-none"
            value={fechaCierre}
            onChange={(e) => setFechaCierre(e.target.value)}
          />
          {erroresServidor["fecha"] ? (
            <p className="mt-1 text-sm text-danger-600" role="alert">
              {erroresServidor["fecha"].join(", ")}
            </p>
          ) : null}
        </FormField>
        <FormField label="Motivo" htmlFor="motivo-cierre">
          <TextInput
            id="motivo-cierre"
            value={motivoCierre}
            onChange={(e) => setMotivoCierre(e.target.value)}
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
          <Button type="submit" variant="primary" disabled={!fechaCierre || !esMotivoValido(motivoCierre) || enviando}>
            Cerrar
          </Button>
          <Button type="button" variant="ghost" onClick={cerrarPanel}>
            Cancelar
          </Button>
        </div>
      </form>
    </section>
  ) : panel === "revocar" ? (
    <section aria-labelledby="revocar-vinculo-titulo" className="mb-8 rounded-lg border border-border-subtle p-4">
      <h2 id="revocar-vinculo-titulo" className="mb-4 text-lg font-semibold text-text-900">
        Revocar vínculo
      </h2>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (fechaRevocacion && esMotivoValido(motivoRevocacion)) void revocar();
        }}
        className="space-y-4"
      >
        <FormField label="Fecha" htmlFor="fecha-revocacion-vinculo">
          <input
            type="date"
            id="fecha-revocacion-vinculo"
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
        <FormField label="Motivo" htmlFor="motivo-revocacion-vinculo">
          <TextInput
            id="motivo-revocacion-vinculo"
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
          <Button type="submit" variant="primary" disabled={!fechaRevocacion || !esMotivoValido(motivoRevocacion) || enviando}>
            Revocar
          </Button>
          <Button type="button" variant="ghost" onClick={cerrarPanel}>
            Cancelar
          </Button>
        </div>
      </form>
    </section>
  ) : null;

  const contexto = detalle.contexto;
  const esHistorica = contexto?.es_historica ?? false;
  const etiquetaCategoria = (categoria: string) =>
    (ETIQUETAS_CATEGORIA_SEPARACION as Record<string, string>)[categoria] ?? categoria;

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Identidad institucional", to: "/gobierno/identidad" },
        ]}
        title={`Vínculo ${detalle.codigo}`}
        description={`${detalle.cuenta.usuario} · ${detalle.funcionario.nombre}`}
      />

      <div className="mb-8 flex flex-wrap items-end gap-4">
        <FormField label="Consultar a la fecha" htmlFor="fecha-consulta">
          <input
            type="date"
            id="fecha-consulta"
            className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900 focus:border-brand-500 focus:outline-none"
            value={fecha}
            onChange={(e) => setFecha(e.target.value)}
          />
        </FormField>
        {contexto && esHistorica ? (
          <p className="text-sm text-warning-700" role="alert">
            Consulta histórica a {formatearFechaDeNegocio(contexto.fecha)}: muestra la situación de entonces y no concede autoridad hoy.
          </p>
        ) : null}
      </div>

      <dl className="mb-8 grid gap-4 sm:grid-cols-2">
        <div>
          <dt className="text-sm font-medium text-text-700">Estado</dt>
          <dd className="mt-1 text-text-900">
            {ETIQUETAS_ESTADO_VINCULO[detalle.status] ?? detalle.status}
          </dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-text-700">Situación</dt>
          <dd className="mt-1 text-text-900">
            {ETIQUETAS_SITUACION_VINCULO[detalle.situacion] ?? detalle.situacion}
          </dd>
        </div>
      </dl>

      <div className="mb-8 flex flex-wrap items-center gap-2">
        {detalle.status === "BORRADOR" && puedeGestionar ? (
          <Link
            to={`/gobierno/identidad/vinculos/${detalle.id}/editar`}
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
          <Button variant="secondary" onClick={() => setPanel("cerrar")}>
            Cerrar
          </Button>
        ) : null}
        {detalle.status === "ACTIVO" && puedeRevocar ? (
          <Button variant="secondary" onClick={() => setPanel("revocar")}>
            Revocar
          </Button>
        ) : null}
      </div>

      {alertaCambio ? (
        <p className="mb-4 text-sm text-danger-600" role="alert">
          {alertaCambio}
        </p>
      ) : null}

      {panelRender}

      <section aria-labelledby="cuenta-funcionario" className="mb-8">
        <h2 id="cuenta-funcionario" className="mb-4 text-lg font-semibold text-text-900">
          Cuenta y funcionario
        </h2>
        <dl className="grid gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-text-700">Cuenta</dt>
            <dd className="mt-1 text-text-900">
              {detalle.cuenta.usuario}
              <span className="block text-sm text-text-500">
                {detalle.cuenta.estado}
              </span>
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Funcionario</dt>
            <dd className="mt-1 text-text-900">
              {detalle.funcionario.nombre}
              <span className="block text-sm text-text-500">
                {detalle.funcionario.codigo} · {detalle.funcionario.documento}
              </span>
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Vigencia</dt>
            <dd className="mt-1 text-text-900">
              {formatearFechaDeNegocio(detalle.desde)} —{" "}
              {detalle.hasta ? formatearFechaDeNegocio(detalle.hasta) : "Sin fecha final"}
              {detalle.fin_efectivo
                ? ` (fin efectivo: ${formatearFechaDeNegocio(detalle.fin_efectivo)})`
                : ""}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Motivo</dt>
            <dd className="mt-1 text-text-900">
              {detalle.motivo || "—"}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Soporte</dt>
            <dd className="mt-1 text-text-900">
              {detalle.soporte || "Sin soporte"}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Registrado por</dt>
            <dd className="mt-1 text-text-900">
              {detalle.registrado_por ?? "—"}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Activado por</dt>
            <dd className="mt-1 text-text-900">
              {detalle.activado_por ?? "—"}
              {detalle.activado_en ? ` · ${formatearFecha(detalle.activado_en)}` : ""}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Terminado por</dt>
            <dd className="mt-1 text-text-900">
              {detalle.terminado_por ?? "—"}
              {detalle.terminado_en ? ` · ${formatearFecha(detalle.terminado_en)}` : ""}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Motivo de fin</dt>
            <dd className="mt-1 text-text-900">
              {detalle.motivo_fin || "—"}
            </dd>
          </div>
        </dl>
      </section>

      {contexto ? (
        <section aria-labelledby="contexto-institucional" className="mb-8">
          <h2 id="contexto-institucional" className="mb-4 text-lg font-semibold text-text-900">
            Contexto institucional a la fecha
          </h2>
          <dl className="grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-sm font-medium text-text-700">Ente</dt>
              <dd className="mt-1 text-text-900">{contexto.ente.nombre}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-text-700">Autoridad</dt>
              <dd className="mt-1 text-text-900">
                {contexto.tiene_autoridad
                  ? "Con autoridad funcional derivada de la ocupación"
                  : contexto.motivo_sin_autoridad
                    ? (ETIQUETAS_MOTIVO_SIN_AUTORIDAD as Record<string, string>)[contexto.motivo_sin_autoridad] ?? contexto.motivo_sin_autoridad
                    : "Sin autoridad"}
              </dd>
            </div>
          </dl>

          <h3 className="mt-6 mb-3 text-base font-semibold text-text-900">
            Ocupaciones
          </h3>
          {contexto.ocupaciones.length === 0 ? (
            <p className="text-sm text-text-700">Sin ocupaciones vigentes en esa fecha</p>
          ) : (
            <div
              className="relative overflow-x-auto"
              tabIndex={0}
              role="region"
              aria-label="Tabla de ocupaciones del contexto institucional"
            >
              <table className="w-full border-collapse text-left">
                <caption className="sr-only">Ocupaciones vigentes en la fecha de consulta</caption>
                <thead>
                  <tr className="border-b border-border-subtle">
                    <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                      Cargo
                    </th>
                    <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                      Unidad
                    </th>
                    <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                      Figura
                    </th>
                    <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                      Ejerce
                    </th>
                    <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                      Vigencia
                    </th>
                    <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                      Autoridad
                    </th>
                    <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                      Avocaciones
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {contexto.ocupaciones.map((o: OcupacionInstitucional, indice: number) => (
                    <tr key={`${o.codigo}-${indice}`} className="border-b border-border-subtle">
                      <td className="px-3 py-2 text-sm text-text-900">
                        {o.asignacion_id ? (
                          <Link
                            to={`/gobierno/ocupacion/asignaciones/${o.asignacion_id}`}
                            className="font-medium text-brand-700 underline"
                          >
                            {o.cargo}
                          </Link>
                        ) : (
                          o.cargo
                        )}
                        {o.cargo_codigo ? (
                          <span className="block text-sm text-text-500">{o.cargo_codigo}</span>
                        ) : null}
                      </td>
                      <td className="px-3 py-2 text-sm text-text-900">{o.unidad}</td>
                      <td className="px-3 py-2 text-sm text-text-900">{o.figura_etiqueta}</td>
                      <td className="px-3 py-2 text-sm text-text-900">{o.ejerce ? "Sí" : "No"}</td>
                      <td className="px-3 py-2 text-sm text-text-900">
                        {formatearFechaDeNegocio(o.desde)} —{" "}
                        {o.hasta ? formatearFechaDeNegocio(o.hasta) : "—"}
                      </td>
                      <td className="px-3 py-2 text-sm text-text-900">
                        {o.autoridad.length === 0
                          ? "Sin autoridad"
                          : o.autoridad.map((c, i) => (
                              <span key={i} className="block">
                                {c.accion} · {c.materia}
                              </span>
                            ))}
                      </td>
                      <td className="px-3 py-2 text-sm text-text-900">{o.avocaciones}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <h3 className="mt-6 mb-3 text-base font-semibold text-text-900">
            Roles
          </h3>
          {contexto.roles.length === 0 ? (
            <p className="text-sm text-text-700">Sin roles</p>
          ) : (
            <ul className="list-disc pl-5 text-sm text-text-900">
              {contexto.roles.map((rol) => (
                <li key={rol.id}>
                  {rol.nombre} <span className="text-text-500">({rol.codigo})</span>
                </li>
              ))}
            </ul>
          )}

          <h3 className="mt-6 mb-3 text-base font-semibold text-text-900">
            Categorías de separación
          </h3>
          {contexto.categorias.length === 0 ? (
            <p className="text-sm text-text-700">Sin categorías de separación</p>
          ) : (
            <ul className="list-disc pl-5 text-sm text-text-900">
              {contexto.categorias.map((categoria) => (
                <li key={categoria}>
                  {etiquetaCategoria(categoria)}
                </li>
              ))}
            </ul>
          )}

          <h3 className="mt-6 mb-3 text-base font-semibold text-text-900">
            Conflictos de separación de funciones
          </h3>
          {contexto.conflictos.length === 0 ? (
            <p className="text-sm text-text-700">Sin conflictos de separación</p>
          ) : (
            <div role="alert" className="rounded-lg border border-danger-300 bg-danger-50 p-4">
              <p className="mb-2 text-sm font-semibold text-danger-900">
                Conflictos de separación de funciones
              </p>
              <ul className="list-disc pl-5 text-sm text-danger-900">
                {contexto.conflictos.map((conflicto, indice) => (
                  <li key={`${conflicto.regla_codigo}-${indice}`}>
                    {conflicto.regla_codigo} · {conflicto.regla_nombre}:{" "}
                    {etiquetaCategoria(conflicto.categoria_a)} y{" "}
                    {etiquetaCategoria(conflicto.categoria_b)}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      ) : null}

      <section aria-labelledby="historia-vinculo">
        <h2 id="historia-vinculo" className="mb-4 text-lg font-semibold text-text-900">
          Historia
        </h2>
        <div
          className="relative overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Tabla de historia del vínculo"
        >
          <table className="w-full border-collapse text-left">
            <caption className="sr-only">Historia del vínculo</caption>
            <thead>
              <tr className="border-b border-border-subtle">
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Fecha
                </th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Tipo
                </th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Actor
                </th>
              </tr>
            </thead>
            <tbody>
              {detalle.historia.map((h: HistoriaIdentidad, indice: number) => (
                <tr key={`${h.tipo}-${h.creado_en}-${indice}`} className="border-b border-border-subtle">
                  <td className="px-3 py-2 text-sm text-text-900">
                    {formatearFecha(h.creado_en)}
                  </td>
                  <td className="px-3 py-2 text-sm text-text-900">
                    {(ETIQUETAS_HISTORIA_VINCULO as Record<string, string>)[h.tipo] ?? h.tipo}
                  </td>
                  <td className="px-3 py-2 text-sm text-text-900">
                    {h.actor ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </PageContent>
  );
}
