import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { useQuery } from "@tanstack/react-query";

import { apiFetch, ApiError } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { TextInput } from "@/components/TextInput";
import { FormField } from "@/components/FormField";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { formatearFecha } from "@/i18n";
import {
  AuditoriaEventos,
  AuditoriaFiltros,
  AuditoriaMuestras,
  CONSULTA_AUDITORIA,
  ETIQUETA_METODO_MUESTREO,
  FiltrosAuditoria,
  POR_PAGINA_AUDITORIA,
  consultaDeAuditoria,
} from "@/modules/gobierno/api";
import { EvidenciaEvento } from "./EvidenciaEvento";
import { RegistrarMuestra } from "./RegistrarMuestra";

const CLASE_SELECT =
  "h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600";

type ParametrosUrl = {
  desde: string;
  hasta: string;
  proceso: string;
  accion: string;
  usuario: string;
  texto: string;
  pagina: string;
  evento: string;
};

function leerParametros(searchParams: URLSearchParams): ParametrosUrl {
  return {
    desde: searchParams.get("desde") ?? "",
    hasta: searchParams.get("hasta") ?? "",
    proceso: searchParams.get("proceso") ?? "",
    accion: searchParams.get("accion") ?? "",
    usuario: searchParams.get("usuario") ?? "",
    texto: searchParams.get("texto") ?? "",
    pagina: searchParams.get("pagina") ?? "",
    evento: searchParams.get("evento") ?? "",
  };
}

function escribirParametros(p: ParametrosUrl): URLSearchParams {
  const search = new URLSearchParams();
  if (p.desde) search.set("desde", p.desde);
  if (p.hasta) search.set("hasta", p.hasta);
  if (p.proceso) search.set("proceso", p.proceso);
  if (p.accion) search.set("accion", p.accion);
  if (p.usuario) search.set("usuario", p.usuario);
  if (p.texto) search.set("texto", p.texto);
  if (p.pagina) search.set("pagina", p.pagina);
  if (p.evento) search.set("evento", p.evento);
  return search;
}

export function AuditoriaInstitucionalPage(): React.JSX.Element {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const [searchParams, setSearchParams] = useSearchParams();

  const parametros = leerParametros(searchParams);
  const puedeVer = tiene("gobierno_auditoria:view", "empresa");
  const puedeMuestrear = tiene("gobierno_auditoria:sample", "empresa");

  const [textoBusqueda, setTextoBusqueda] = useState(parametros.texto);
  const [usuarioBusqueda, setUsuarioBusqueda] = useState(parametros.usuario);
  const [mostrarRegistro, setMostrarRegistro] = useState(false);
  const [seleccion, setSeleccion] = useState<Set<string>>(new Set());

  useEffect(() => {
    setTextoBusqueda(parametros.texto);
  }, [parametros.texto]);

  useEffect(() => {
    setUsuarioBusqueda(parametros.usuario);
  }, [parametros.usuario]);

  const consultaFiltros = useQuery({
    queryKey: [...CONSULTA_AUDITORIA, activeCompanyId, "filtros"],
    queryFn: () =>
      apiFetch<AuditoriaFiltros>("/gobierno/auditoria/filtros"),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
  });

  const filtros = useMemo<FiltrosAuditoria>(() => {
    return {
      desde: parametros.desde || undefined,
      hasta: parametros.hasta || undefined,
      proceso: parametros.proceso || undefined,
      accion: parametros.accion || undefined,
      usuario: parametros.usuario || undefined,
      texto: parametros.texto || undefined,
    };
  }, [
    parametros.desde,
    parametros.hasta,
    parametros.proceso,
    parametros.accion,
    parametros.usuario,
    parametros.texto,
  ]);

  const rangoInvalido =
    parametros.desde !== "" &&
    parametros.hasta !== "" &&
    parametros.desde > parametros.hasta;

  const paginaActual =
    parametros.pagina && Number(parametros.pagina) > 0
      ? Number(parametros.pagina)
      : 1;

  const consultaEventos = useQuery({
    queryKey: [
      ...CONSULTA_AUDITORIA,
      activeCompanyId,
      "eventos",
      filtros,
      paginaActual,
    ],
    queryFn: () =>
      apiFetch<AuditoriaEventos>(
        `/gobierno/auditoria/eventos${consultaDeAuditoria(filtros, {
          pagina: paginaActual,
          por_pagina: POR_PAGINA_AUDITORIA,
        })}`,
      ),
    enabled: puedeVer && Boolean(activeCompanyId) && !rangoInvalido,
    retry: false,
  });

  const consultaMuestras = useQuery({
    queryKey: [...CONSULTA_AUDITORIA, activeCompanyId, "muestras"],
    queryFn: () =>
      apiFetch<AuditoriaMuestras>("/gobierno/auditoria/muestras"),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
  });

  const tieneFiltrosActivos =
    parametros.desde !== "" ||
    parametros.hasta !== "" ||
    parametros.proceso !== "" ||
    parametros.accion !== "" ||
    parametros.usuario !== "" ||
    parametros.texto !== "";

  const cambiarParametros = (
    cambios: Partial<Record<keyof ParametrosUrl, string>>,
  ) => {
    const siguientes = {
      ...parametros,
      ...cambios,
    };
    setSearchParams(escribirParametros(siguientes), { replace: true });
  };

  const cambiarFiltro = (
    cambios: Partial<Record<keyof ParametrosUrl, string>>,
  ) => {
    setSeleccion(new Set());
    cambiarParametros({
      ...cambios,
      pagina: "",
      evento: "",
    });
  };

  const limpiarFiltros = () => {
    setSeleccion(new Set());
    const siguientes = {
      ...parametros,
      desde: "",
      hasta: "",
      proceso: "",
      accion: "",
      usuario: "",
      texto: "",
      pagina: "",
      evento: "",
    };
    setSearchParams(escribirParametros(siguientes), { replace: true });
  };

  const cabecera = (
    <PageHeader
      crumbs={[{ label: "Gobierno" }, { label: "Auditoría institucional" }]}
      title="Auditoría institucional"
      description="Consulta y muestreo de solo lectura de la actividad de Gobierno del ente (GOV-CTL-005)."
      actions={
        puedeMuestrear ? (
          <Button onClick={() => setMostrarRegistro(true)}>
            Registrar muestra
          </Button>
        ) : undefined
      }
    />
  );

  const accionesDisponibles = useMemo(() => {
    if (!consultaFiltros.data) return [];
    if (!parametros.proceso) return consultaFiltros.data.acciones;
    return consultaFiltros.data.acciones.filter(
      (accion) => accion.proceso === parametros.proceso,
    );
  }, [consultaFiltros.data, parametros.proceso]);

  if (!puedeVer) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para consultar la auditoría institucional."
        />
      </PageContent>
    );
  }

  let contenidoEventos: React.JSX.Element;

  if (rangoInvalido) {
    contenidoEventos = (
      <EmptyState
        title="Rango de fechas inválido"
        description="La fecha inicial es posterior a la final."
      />
    );
  } else if (consultaEventos.isLoading) {
    contenidoEventos = <LoadingState label="Cargando la población…" />;
  } else if (consultaEventos.isError) {
    const error = consultaEventos.error;
    if (
      error instanceof ApiError &&
      error.status === 403 &&
      error.code === "MODULE_NOT_ENTITLED"
    ) {
      contenidoEventos = (
        <EmptyState
          title="Módulo no disponible"
          description="El módulo de Gobierno no está habilitado."
        />
      );
    } else if (
      error instanceof ApiError &&
      (error.status === 403 || error.status === 401)
    ) {
      contenidoEventos = (
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para consultar la auditoría institucional."
        />
      );
    } else if (
      error instanceof ApiError &&
      error.status === 422 &&
      error.code === "INVALID_DATE_RANGE"
    ) {
      contenidoEventos = (
        <EmptyState
          title="Rango de fechas inválido"
          description="La fecha inicial es posterior a la final."
        />
      );
    } else {
      contenidoEventos = (
        <ErrorState
          message="No fue posible cargar la población."
          onRetry={() => void consultaEventos.refetch()}
        />
      );
    }
  } else {
    const eventos = consultaEventos.data;
    if (!eventos) {
      contenidoEventos = (
        <ErrorState
          message="No fue posible cargar la población."
          onRetry={() => void consultaEventos.refetch()}
        />
      );
    } else if (eventos.items.length === 0) {
      if (tieneFiltrosActivos) {
        contenidoEventos = (
          <EmptyState
            title="Ninguna actividad de Gobierno coincide con los filtros"
            action={
              <Button variant="ghost" onClick={limpiarFiltros}>
                Limpiar filtros
              </Button>
            }
          />
        );
      } else {
        contenidoEventos = (
          <EmptyState title="Sin actividad de Gobierno registrada en este ente" />
        );
      }
    } else {
      const totalPaginas = Math.max(
        1,
        Math.ceil(eventos.total / eventos.por_pagina),
      );

      const alternarSeleccion = (eventoId: string) => {
        setSeleccion((previas) => {
          const siguientes = new Set(previas);
          if (siguientes.has(eventoId)) {
            siguientes.delete(eventoId);
          } else {
            siguientes.add(eventoId);
          }
          return siguientes;
        });
      };

      contenidoEventos = (
        <>
          <p aria-live="polite" className="mb-3 text-sm text-text-600">
            {`${eventos.total} ${eventos.total === 1 ? "evento" : "eventos"} en la población`}
          </p>

          {puedeMuestrear && seleccion.size > 0 ? (
            <div className="mb-3 flex items-center gap-3">
              <p className="text-sm text-text-600">
                {`${seleccion.size} ${seleccion.size === 1 ? "partida marcada" : "partidas marcadas"}`}
              </p>
              <Button variant="ghost" onClick={() => setSeleccion(new Set())}>
                Desmarcar todas
              </Button>
            </div>
          ) : null}

          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Población de eventos de Gobierno"
          >
            <table className="w-full min-w-[960px] border-collapse text-sm">
              <caption className="sr-only">
                Población de eventos de Gobierno
              </caption>
              <thead>
                <tr className="border-b border-border-default text-left text-text-600">
                  {puedeMuestrear ? (
                    <th className="px-3 py-2 font-medium">Marcar</th>
                  ) : null}
                  <th className="px-3 py-2 font-medium">Fecha y hora</th>
                  <th className="px-3 py-2 font-medium">Proceso</th>
                  <th className="px-3 py-2 font-medium">Acción</th>
                  <th className="px-3 py-2 font-medium">Objeto</th>
                  <th className="px-3 py-2 font-medium">Usuario</th>
                  <th className="px-3 py-2 font-medium">Motivo</th>
                  <th className="px-3 py-2 font-medium">Evidencia</th>
                </tr>
              </thead>
              <tbody>
                {eventos.items.map((evento) => (
                  <tr
                    key={evento.id}
                    className="border-b border-border-default align-top"
                  >
                    {puedeMuestrear ? (
                      <td className="px-3 py-2">
                        <input
                          type="checkbox"
                          aria-label={`Marcar el evento ${evento.accion_etiqueta} del ${formatearFecha(evento.fecha)}`}
                          checked={seleccion.has(evento.id)}
                          onChange={() => alternarSeleccion(evento.id)}
                        />
                      </td>
                    ) : null}
                    <td className="px-3 py-2 whitespace-nowrap">
                      {formatearFecha(evento.fecha)}
                    </td>
                    <td className="px-3 py-2">
                      {`${evento.proceso} · ${evento.proceso_nombre}`}
                    </td>
                    <td className="px-3 py-2">{evento.accion_etiqueta}</td>
                    <td className="px-3 py-2">
                      {evento.entidad}
                      {evento.entidad_id ? (
                        <span className="ml-1 text-xs text-text-600">
                          {evento.entidad_id}
                        </span>
                      ) : null}
                    </td>
                    <td className="px-3 py-2">{evento.usuario ?? "—"}</td>
                    <td className="px-3 py-2">{evento.motivo ?? "—"}</td>
                    <td className="px-3 py-2">
                      <Button
                        variant="ghost"
                        aria-label={`Ver evidencia del evento ${evento.accion_etiqueta} del ${formatearFecha(evento.fecha)}`}
                        onClick={() => cambiarParametros({ evento: evento.id })}
                      >
                        Ver evidencia
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {eventos.total > eventos.por_pagina ? (
            <div className="mt-4 flex items-center justify-between">
              <p className="text-sm text-text-600">
                Página {eventos.pagina} de {totalPaginas}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  onClick={() =>
                    cambiarParametros({
                      pagina: String(Math.max(1, eventos.pagina - 1)),
                      evento: "",
                    })
                  }
                  disabled={eventos.pagina <= 1}
                >
                  Anterior
                </Button>
                <Button
                  variant="secondary"
                  onClick={() =>
                    cambiarParametros({
                      pagina: String(
                        Math.min(totalPaginas, eventos.pagina + 1),
                      ),
                      evento: "",
                    })
                  }
                  disabled={eventos.pagina >= totalPaginas}
                >
                  Siguiente
                </Button>
              </div>
            </div>
          ) : null}
        </>
      );
    }
  }

  let contenidoMuestras: React.JSX.Element;

  if (consultaMuestras.isLoading) {
    contenidoMuestras = <LoadingState label="Cargando las muestras…" />;
  } else if (consultaMuestras.isError) {
    const error = consultaMuestras.error;
    if (
      error instanceof ApiError &&
      error.status === 403 &&
      error.code === "MODULE_NOT_ENTITLED"
    ) {
      contenidoMuestras = (
        <EmptyState
          title="Módulo no disponible"
          description="El módulo de Gobierno no está habilitado."
        />
      );
    } else {
      contenidoMuestras = (
        <ErrorState
          message="No fue posible cargar las muestras guardadas."
          onRetry={() => void consultaMuestras.refetch()}
        />
      );
    }
  } else {
    const muestras = consultaMuestras.data;
    if (!muestras || muestras.items.length === 0) {
      contenidoMuestras = (
        <EmptyState title="Aún no hay muestras registradas" />
      );
    } else {
      contenidoMuestras = (
        <div
          className="relative overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Tabla de muestras guardadas"
        >
          <table className="w-full min-w-[720px] border-collapse text-sm">
            <caption className="sr-only">Muestras guardadas</caption>
            <thead>
              <tr className="border-b border-border-default text-left text-text-600">
                <th className="px-3 py-2 font-medium">Código</th>
                <th className="px-3 py-2 font-medium">Título</th>
                <th className="px-3 py-2 font-medium">Medio</th>
                <th className="px-3 py-2 font-medium">Partidas</th>
                <th className="px-3 py-2 font-medium">Registrada por</th>
                <th className="px-3 py-2 font-medium">Registrada el</th>
              </tr>
            </thead>
            <tbody>
              {muestras.items.map((muestra) => (
                <tr
                  key={muestra.id}
                  className="border-b border-border-default align-top"
                >
                  <td className="px-3 py-2">
                    <Link
                      to={`/gobierno/auditoria/muestras/${muestra.id}`}
                      className="text-brand-600 hover:underline"
                    >
                      {muestra.codigo}
                    </Link>
                  </td>
                  <td className="px-3 py-2">{muestra.titulo}</td>
                  <td className="px-3 py-2">
                    {ETIQUETA_METODO_MUESTREO[muestra.metodo] ??
                      muestra.metodo}
                  </td>
                  <td className="px-3 py-2">
                    {`${muestra.tamano} de ${muestra.poblacion}`}
                  </td>
                  <td className="px-3 py-2">
                    {muestra.registrada_por ?? "—"}
                  </td>
                  <td className="px-3 py-2">
                    {formatearFecha(muestra.registrada_en)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }
  }

  return (
    <PageContent>
      {cabecera}

      <p
        role="note"
        className="mb-6 border-l-4 border-brand-600 bg-brand-50 px-4 py-3 text-sm text-text-700"
      >
        Vista de solo lectura: la bitácora no se modifica. La única escritura
        es la muestra, que queda guardada como papel de trabajo.
      </p>

      <div className="mb-6 flex flex-wrap items-end gap-3">
        <FormField label="Desde" htmlFor="filtro-desde" className="min-w-40">
          <input
            id="filtro-desde"
            type="date"
            className={CLASE_SELECT}
            value={parametros.desde}
            onChange={(e) => cambiarFiltro({ desde: e.target.value })}
          />
        </FormField>

        <FormField
          label="Hasta"
          htmlFor="filtro-hasta"
          className="min-w-40"
          error={
            rangoInvalido
              ? "La fecha inicial es posterior a la final."
              : undefined
          }
        >
          <input
            id="filtro-hasta"
            type="date"
            className={CLASE_SELECT}
            value={parametros.hasta}
            onChange={(e) => cambiarFiltro({ hasta: e.target.value })}
          />
        </FormField>

        <FormField label="Proceso" htmlFor="filtro-proceso" className="min-w-44">
          <select
            id="filtro-proceso"
            className={CLASE_SELECT}
            value={parametros.proceso}
            onChange={(e) =>
              cambiarFiltro({ proceso: e.target.value, accion: "" })
            }
          >
            <option value="">Todos</option>
            {(consultaFiltros.data?.procesos ?? []).map((proceso) => (
              <option key={proceso.codigo} value={proceso.codigo}>
                {`${proceso.codigo} · ${proceso.nombre}`}
              </option>
            ))}
          </select>
        </FormField>

        <FormField label="Acción" htmlFor="filtro-accion" className="min-w-44">
          <select
            id="filtro-accion"
            className={CLASE_SELECT}
            value={parametros.accion}
            onChange={(e) => cambiarFiltro({ accion: e.target.value })}
          >
            <option value="">Todas</option>
            {accionesDisponibles.map((accion) => (
              <option key={accion.codigo} value={accion.codigo}>
                {accion.etiqueta}
              </option>
            ))}
          </select>
        </FormField>

        <form
          className="flex min-w-96 flex-1 items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            cambiarFiltro({
              usuario: usuarioBusqueda.trim(),
              texto: textoBusqueda.trim(),
            });
          }}
        >
          <FormField
            label="Usuario"
            htmlFor="filtro-usuario"
            className="min-w-40"
          >
            <TextInput
              id="filtro-usuario"
              name="usuario"
              value={usuarioBusqueda}
              onChange={(e) => setUsuarioBusqueda(e.target.value)}
              placeholder="Usuario"
            />
          </FormField>
          <FormField
            label="Buscar"
            htmlFor="filtro-texto"
            className="min-w-56 flex-1"
          >
            <TextInput
              id="filtro-texto"
              name="texto"
              value={textoBusqueda}
              onChange={(e) => setTextoBusqueda(e.target.value)}
              placeholder="Motivo, usuario o acción"
            />
          </FormField>
          <Button type="submit" variant="secondary">
            Buscar
          </Button>
        </form>

        <Button variant="ghost" onClick={limpiarFiltros}>
          Limpiar filtros
        </Button>
      </div>

      <section>
        {contenidoEventos}
      </section>

      {parametros.evento ? (
        <EvidenciaEvento
          eventoId={parametros.evento}
          onCerrar={() => cambiarParametros({ evento: "" })}
        />
      ) : null}

      {mostrarRegistro && puedeMuestrear ? (
        <div className="mt-8 border-t border-border-default pt-6">
          <RegistrarMuestra
            filtros={filtros}
            seleccion={[...seleccion]}
            onCancelar={() => setMostrarRegistro(false)}
          />
        </div>
      ) : null}

      <section
        aria-labelledby="muestras-guardadas-titulo"
        className="mt-8"
      >
        <h2
          id="muestras-guardadas-titulo"
          className="mb-4 text-lg font-semibold text-text-900"
        >
          Muestras guardadas
        </h2>
        {contenidoMuestras}
      </section>
    </PageContent>
  );
}
