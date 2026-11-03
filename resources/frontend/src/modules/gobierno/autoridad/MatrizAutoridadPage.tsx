import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { Download, X } from "lucide-react";

import { apiFetch, ApiError } from "@/api/client";
import { descargarArchivo } from "@/api/descargas";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { TextInput } from "@/components/TextInput";
import { FormField } from "@/components/FormField";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { formatearFecha } from "@/i18n";
import { hoyDeNegocio, formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_AUTORIDAD,
  ETIQUETA_ACCION,
  ETIQUETA_ESTADO_CARGO,
  ETIQUETA_MATERIA,
  POR_PAGINA_MATRIZ,
  consultaDeMatriz,
  describirLimite,
  type FiltrosMatriz,
  type MatrizAutoridad,
  type MatrizDetalleCargo,
  type MatrizEjercicios,
  type MatrizFiltros,
} from "@/modules/gobierno/api";

const CLASE_SELECT =
  "h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600";

type ParametrosUrl = {
  ejercicio: string;
  fecha: string;
  unidad: string;
  cargo: string;
  accion: string;
  materia: string;
  texto: string;
  pagina: string;
  detalle: string;
};

function leerParametros(searchParams: URLSearchParams): ParametrosUrl {
  return {
    ejercicio: searchParams.get("ejercicio") ?? "",
    fecha: searchParams.get("fecha") ?? "",
    unidad: searchParams.get("unidad") ?? "",
    cargo: searchParams.get("cargo") ?? "",
    accion: searchParams.get("accion") ?? "",
    materia: searchParams.get("materia") ?? "",
    texto: searchParams.get("texto") ?? "",
    pagina: searchParams.get("pagina") ?? "",
    detalle: searchParams.get("detalle") ?? "",
  };
}

function escribirParametros(p: ParametrosUrl): URLSearchParams {
  const search = new URLSearchParams();
  if (p.ejercicio) search.set("ejercicio", p.ejercicio);
  if (p.fecha) search.set("fecha", p.fecha);
  if (p.unidad) search.set("unidad", p.unidad);
  if (p.cargo) search.set("cargo", p.cargo);
  if (p.accion) search.set("accion", p.accion);
  if (p.materia) search.set("materia", p.materia);
  if (p.texto) search.set("texto", p.texto);
  if (p.pagina) search.set("pagina", p.pagina);
  if (p.detalle) search.set("detalle", p.detalle);
  return search;
}



export function MatrizAutoridadPage(): React.JSX.Element {
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const [searchParams, setSearchParams] = useSearchParams();

  const parametros = leerParametros(searchParams);
  const puedeVer = tiene("gobierno_autoridad:view", "empresa");
  const puedeAbrirCargo = tiene("gobierno_cargos:view", "empresa");
  const [textoBusqueda, setTextoBusqueda] = useState(parametros.texto);

  useEffect(() => {
    setTextoBusqueda(parametros.texto);
  }, [parametros.texto]);

  const consultaEjercicios = useQuery({
    queryKey: [...CONSULTA_AUTORIDAD, "ejercicios"],
    queryFn: () =>
      apiFetch<MatrizEjercicios>("/gobierno/autoridad/ejercicios"),
    enabled: puedeVer,
    retry: false,
  });

  const ejercicioEfectivo = useMemo(() => {
    const items = consultaEjercicios.data?.items ?? [];
    if (items.length === 0) return "";

    const ejercicioUrl = Number(parametros.ejercicio);
    if (items.some((item) => item.ejercicio === ejercicioUrl)) {
      return String(ejercicioUrl);
    }

    const anioActual = Number(hoyDeNegocio().slice(0, 4));
    if (items.some((item) => item.ejercicio === anioActual)) {
      return String(anioActual);
    }

    return String(items[0].ejercicio);
  }, [consultaEjercicios.data?.items, parametros.ejercicio]);

  const consultaFiltros = useQuery({
    queryKey: [...CONSULTA_AUTORIDAD, "filtros", ejercicioEfectivo],
    queryFn: () =>
      apiFetch<MatrizFiltros>(
        `/gobierno/autoridad/${ejercicioEfectivo}/filtros`,
      ),
    enabled: puedeVer && ejercicioEfectivo !== "",
    retry: false,
  });

  const filtrosValidos = useMemo<FiltrosMatriz>(() => {
    const accionValida = parametros.accion
      ? (Object.keys(ETIQUETA_ACCION).includes(parametros.accion)
          ? (parametros.accion as FiltrosMatriz["accion"])
          : undefined)
      : undefined;
    const materiaValida = parametros.materia
      ? (Object.keys(ETIQUETA_MATERIA).includes(parametros.materia)
          ? (parametros.materia as FiltrosMatriz["materia"])
          : undefined)
      : undefined;

    return {
      fecha: parametros.fecha,
      unidad_id: parametros.unidad || undefined,
      cargo_id: parametros.cargo || undefined,
      accion: accionValida,
      materia: materiaValida,
      texto: parametros.texto || undefined,
    };
  }, [
    parametros.fecha,
    parametros.unidad,
    parametros.cargo,
    parametros.accion,
    parametros.materia,
    parametros.texto,
  ]);

  const paginaActual =
    parametros.pagina && Number(parametros.pagina) > 0
      ? Number(parametros.pagina)
      : 1;

  const consultaMatriz = useQuery({
    queryKey: [
      ...CONSULTA_AUTORIDAD,
      "matriz",
      ejercicioEfectivo,
      filtrosValidos,
      paginaActual,
    ],
    queryFn: () =>
      apiFetch<MatrizAutoridad>(
        `/gobierno/autoridad/${ejercicioEfectivo}${consultaDeMatriz(
          filtrosValidos,
          { pagina: paginaActual, por_pagina: POR_PAGINA_MATRIZ },
        )}`,
      ),
    enabled: puedeVer && ejercicioEfectivo !== "",
    retry: false,
  });

  const detalleCargoId = parametros.detalle || undefined;
  const consultaDetalle = useQuery({
    queryKey: [
      ...CONSULTA_AUTORIDAD,
      "detalle",
      ejercicioEfectivo,
      detalleCargoId,
    ],
    queryFn: () =>
      apiFetch<MatrizDetalleCargo>(
        `/gobierno/autoridad/${ejercicioEfectivo}/cargos/${detalleCargoId}`,
      ),
    enabled: puedeVer && ejercicioEfectivo !== "" && detalleCargoId !== undefined,
    retry: false,
  });

  const tieneFiltrosActivos =
    parametros.unidad !== "" ||
    parametros.cargo !== "" ||
    parametros.accion !== "" ||
    parametros.materia !== "" ||
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
    cambiarParametros({
      ...cambios,
      pagina: "",
      detalle: "",
    });
  };

  const limpiarFiltros = () => {
    const siguientes = {
      ...parametros,
      unidad: "",
      cargo: "",
      accion: "",
      materia: "",
      texto: "",
      pagina: "",
      detalle: "",
    };
    setSearchParams(escribirParametros(siguientes), { replace: true });
  };

  const fechaMostrada =
    parametros.fecha || consultaMatriz.data?.fecha || hoyDeNegocio();

  const exportarCsv = async () => {
    if (ejercicioEfectivo === "") return;
    try {
      await descargarArchivo(
        `/gobierno/autoridad/${ejercicioEfectivo}/exportar${consultaDeMatriz(
          filtrosValidos,
        )}`,
        `autoridad-${ejercicioEfectivo}-${consultaMatriz.data?.fecha ?? fechaMostrada}.csv`,
      );
      notify({ type: "success", title: "Matriz exportada" });
    } catch {
      notify({ type: "error", title: "No fue posible exportar" });
    }
  };

  const crumbs = [
    { label: "Gobierno" },
    { label: "Matriz de autoridad", to: "/gobierno/autoridad" },
  ];

  const cabecera = (
    <PageHeader
      crumbs={crumbs}
      title="Matriz de autoridad"
      description="Quién puede, por cargo, solicitar, comprometer, causar, ordenar el pago, pagar, registrar, custodiar, aprobar, auditar o firmar (GOV-ORG-010)."
      actions={
        puedeVer && ejercicioEfectivo !== "" ? (
          <AsyncButton onClick={exportarCsv} variant="secondary">
            <Download className="mr-2 h-4 w-4" aria-hidden="true" />
            Exportar CSV
          </AsyncButton>
        ) : undefined
      }
    />
  );

  if (!puedeVer) {
    return (
      <PageContent>
        <PageHeader
          crumbs={crumbs}
          title="Matriz de autoridad"
          description="Quién puede, por cargo, solicitar, comprometer, causar, ordenar el pago, pagar, registrar, custodiar, aprobar, auditar o firmar (GOV-ORG-010)."
        />
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver la matriz de autoridad."
        />
      </PageContent>
    );
  }

  if (consultaEjercicios.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando la matriz de autoridad…" />
      </PageContent>
    );
  }

  if (consultaEjercicios.isError) {
    const error = consultaEjercicios.error;
    if (
      error instanceof ApiError &&
      error.status === 403 &&
      error.code === "MODULE_NOT_ENTITLED"
    ) {
      return (
        <PageContent>
          {cabecera}
          <EmptyState
            title="Módulo no disponible"
            description="El módulo de Gobierno no está habilitado."
          />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          {cabecera}
          <EmptyState
            title="Sin acceso"
            description="No tiene permiso para ver la matriz de autoridad."
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar la matriz de autoridad."
          onRetry={() => void consultaEjercicios.refetch()}
        />
      </PageContent>
    );
  }

  if (!consultaEjercicios.data || consultaEjercicios.data.items.length === 0) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Sin estructuras organizativas"
          description="Registre primero la estructura del ejercicio en Gobierno › Estructura organizativa."
        />
      </PageContent>
    );
  }

  const errorFecha =
    consultaMatriz.isError &&
    consultaMatriz.error instanceof ApiError &&
    consultaMatriz.error.status === 422 &&
    consultaMatriz.error.code === "GOV_AUTHORITY_DATE_OUT_OF_EXERCISE"
      ? consultaMatriz.error
      : undefined;

  const matriz = consultaMatriz.data;
  const cargandoMatriz = consultaMatriz.isLoading;
  const sinMatrizError =
    consultaMatriz.isError && !errorFecha ? consultaMatriz.error : undefined;

  let contenidoMatriz: React.JSX.Element;

  if (cargandoMatriz) {
    contenidoMatriz = <LoadingState label="Cargando la matriz de autoridad…" />;
  } else if (sinMatrizError) {
    const error = sinMatrizError;
    if (
      error instanceof ApiError &&
      error.status === 403 &&
      error.code === "MODULE_NOT_ENTITLED"
    ) {
      contenidoMatriz = (
        <EmptyState
          title="Módulo no disponible"
          description="El módulo de Gobierno no está habilitado."
        />
      );
    } else if (error instanceof ApiError && error.status === 403) {
      contenidoMatriz = (
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver la matriz de autoridad."
        />
      );
    } else if (
      error instanceof ApiError &&
      error.status === 404 &&
      error.code === "GOV_STRUCTURE_NOT_FOUND"
    ) {
      contenidoMatriz = (
        <EmptyState
          title="Sin estructuras organizativas"
          description="Registre primero la estructura del ejercicio en Gobierno › Estructura organizativa."
        />
      );
    } else {
      contenidoMatriz = (
        <ErrorState
          message="No fue posible cargar la matriz de autoridad."
          onRetry={() => void consultaMatriz.refetch()}
        />
      );
    }
  } else if (!matriz) {
    contenidoMatriz = (
      <ErrorState
        message="No fue posible cargar la matriz de autoridad."
        onRetry={() => void consultaMatriz.refetch()}
      />
    );
  } else if (matriz.items.length === 0) {
    if (tieneFiltrosActivos) {
      contenidoMatriz = (
        <EmptyState
          title="Ninguna autorización coincide con los filtros"
          action={
            <Button variant="ghost" onClick={limpiarFiltros}>
              Limpiar filtros
            </Button>
          }
        />
      );
    } else {
      contenidoMatriz = (
        <EmptyState
          title={`Sin autoridad registrada al ${formatearFechaDeNegocio(
            fechaMostrada,
          )}`}
          description="Ningún cargo vigente en esa fecha tiene competencias."
        />
      );
    }
  } else {
    const totalPaginas = Math.max(
      1,
      Math.ceil(matriz.total / matriz.por_pagina),
    );

    const versionUsadaPorCargo = new Map<string, number>();
    matriz.items.forEach((fila) => {
      if (fila.version?.version) {
        versionUsadaPorCargo.set(String(fila.cargo_id), fila.version.version);
      }
    });

    contenidoMatriz = (
      <>
        <p aria-live="polite" className="mb-3 text-sm text-text-600">
          {`${matriz.total} ${matriz.total === 1 ? "autorización" : "autorizaciones"} de ${matriz.cargos} ${matriz.cargos === 1 ? "cargo" : "cargos"} al ${formatearFechaDeNegocio(matriz.fecha)}`}
        </p>

        <div
          className="relative overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label={`Matriz de autoridad al ${formatearFechaDeNegocio(matriz.fecha)}`}
        >
          <table className="w-full min-w-[960px] border-collapse text-sm">
            <caption className="sr-only">
              Matriz de autoridad al {formatearFechaDeNegocio(matriz.fecha)}
            </caption>
            <thead>
              <tr className="border-b border-border-default text-left text-text-600">
                <th scope="col" className="px-3 py-2 font-medium">
                  Cargo
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Unidad
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Acción
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Materia
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Límite
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Vigencia
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Acto soporte
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  <span className="sr-only">Detalle</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {matriz.items.map((fila) => {
                const actosSoporte = (fila.acto_soporte ?? []).join(" · ");

                return (
                  <tr
                    key={fila.id}
                    className="border-b border-border-subtle align-top"
                  >
                    <td className="px-3 py-2 text-text-900">
                      <div className="font-semibold">{fila.cargo_codigo}</div>
                      <div className="text-text-700">
                        {fila.cargo_denominacion}
                      </div>
                      {fila.estado_cargo === "INACTIVO" ? (
                        <div className="text-xs text-text-600">Inactivo</div>
                      ) : null}
                    </td>
                    <td className="px-3 py-2 text-text-900">
                      <div>
                        {fila.unidad_denominacion ?? fila.unidad_codigo}
                      </div>
                      {fila.ruta_unidad ? (
                        <div className="text-xs text-text-600">
                          {fila.ruta_unidad}
                        </div>
                      ) : null}
                    </td>
                    <td className="px-3 py-2 text-text-700">
                      {ETIQUETA_ACCION[fila.accion]}
                    </td>
                    <td className="px-3 py-2 text-text-700">
                      {ETIQUETA_MATERIA[fila.materia]}
                    </td>
                    <td className="px-3 py-2 text-text-700">
                      <div>{describirLimite(fila)}</div>
                      {fila.fundamento ? (
                        <div className="text-xs text-text-600">
                          {fila.fundamento}
                        </div>
                      ) : null}
                    </td>
                    <td className="px-3 py-2 text-text-700">
                      {fila.vigente_hasta
                        ? `${formatearFechaDeNegocio(
                            fila.vigente_desde,
                          )} – ${formatearFechaDeNegocio(fila.vigente_hasta)}`
                        : `Desde ${formatearFechaDeNegocio(fila.vigente_desde)}`}
                    </td>
                    <td className="px-3 py-2 text-text-700">
                      {actosSoporte || "Sin documento"}
                    </td>
                    <td className="px-3 py-2">
                      <Button
                        variant="ghost"
                        onClick={() =>
                          cambiarParametros({
                            detalle: String(fila.cargo_id),
                          })
                        }
                        aria-label={`Ver el detalle de ${fila.cargo_codigo}`}
                      >
                        Ver detalle
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {matriz.total > matriz.por_pagina ? (
          <div className="mt-4 flex items-center justify-between">
            <p className="text-sm text-text-600">
              Página {matriz.pagina} de {totalPaginas}
            </p>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                onClick={() =>
                  cambiarParametros({
                    pagina: String(Math.max(1, matriz.pagina - 1)),
                    detalle: "",
                  })
                }
                disabled={matriz.pagina <= 1}
              >
                Anterior
              </Button>
              <Button
                variant="secondary"
                onClick={() =>
                  cambiarParametros({
                    pagina: String(Math.min(totalPaginas, matriz.pagina + 1)),
                    detalle: "",
                  })
                }
                disabled={matriz.pagina >= totalPaginas}
              >
                Siguiente
              </Button>
            </div>
          </div>
        ) : null}
      </>
    );
  }

  const detalle = consultaDetalle.data;
  const filaDetalle = matriz?.items.find(
    (fila) => String(fila.cargo_id) === detalleCargoId,
  );
  const versionUsada = filaDetalle?.version?.version;

  return (
    <PageContent>
      {cabecera}

      <p
        role="note"
        className="mb-6 border-l-4 border-brand-600 bg-brand-50 px-4 py-3 text-sm text-text-700"
      >
        La autoridad es la de cada cargo. Las personas que ocupan los cargos
        llegarán con la vinculación de usuarios a cargos (ORG-06), y las
        delegaciones, suplencias y encargadurías con ORG-04.
      </p>

      <div className="mb-6 flex flex-wrap items-end gap-3">
        <FormField
          label="Ejercicio"
          htmlFor="filtro-ejercicio"
          className="min-w-32"
        >
          <select
            id="filtro-ejercicio"
            className={CLASE_SELECT}
            value={ejercicioEfectivo}
            onChange={(e) =>
              cambiarFiltro({ ejercicio: e.target.value, fecha: "" })
            }
          >
            {consultaEjercicios.data.items.map((item) => (
              <option key={item.ejercicio} value={item.ejercicio}>
                {item.ejercicio}
              </option>
            ))}
          </select>
        </FormField>

        <FormField
          label="A la fecha"
          htmlFor="filtro-fecha"
          className="min-w-40"
          error={
            errorFecha
              ? (errorFecha.fieldErrors?.fecha?.[0] ??
                "La fecha no pertenece al ejercicio.")
              : undefined
          }
        >
          <input
            type="date"
            id="filtro-fecha"
            className={CLASE_SELECT}
            min={`${ejercicioEfectivo}-01-01`}
            max={`${ejercicioEfectivo}-12-31`}
            value={parametros.fecha || matriz?.fecha || ""}
            onChange={(e) => cambiarFiltro({ fecha: e.target.value })}
          />
        </FormField>

        <FormField label="Unidad" htmlFor="filtro-unidad" className="min-w-56">
          <select
            id="filtro-unidad"
            className={CLASE_SELECT}
            value={parametros.unidad}
            onChange={(e) => cambiarFiltro({ unidad: e.target.value })}
          >
            <option value="">Todas</option>
            {(consultaFiltros.data?.unidades ?? []).map((unidad) => (
              <option key={unidad.id} value={unidad.id}>
                {unidad.ruta} · {unidad.denominacion}
              </option>
            ))}
          </select>
        </FormField>

        <FormField label="Cargo" htmlFor="filtro-cargo" className="min-w-56">
          <select
            id="filtro-cargo"
            className={CLASE_SELECT}
            value={parametros.cargo}
            onChange={(e) => cambiarFiltro({ cargo: e.target.value })}
          >
            <option value="">Todos</option>
            {(consultaFiltros.data?.cargos ?? []).map((cargo) => (
              <option key={cargo.id} value={cargo.id}>
                {cargo.codigo} · {cargo.denominacion}
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
            {Object.entries(ETIQUETA_ACCION).map(([valor, etiqueta]) => (
              <option key={valor} value={valor}>
                {etiqueta}
              </option>
            ))}
          </select>
        </FormField>

        <FormField label="Materia" htmlFor="filtro-materia" className="min-w-44">
          <select
            id="filtro-materia"
            className={CLASE_SELECT}
            value={parametros.materia}
            onChange={(e) => cambiarFiltro({ materia: e.target.value })}
          >
            <option value="">Todas</option>
            {Object.entries(ETIQUETA_MATERIA).map(([valor, etiqueta]) => (
              <option key={valor} value={valor}>
                {etiqueta}
              </option>
            ))}
          </select>
        </FormField>

        <form
          className="flex min-w-72 flex-1 items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            cambiarFiltro({ texto: textoBusqueda.trim() });
          }}
        >
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
              placeholder="Cargo, unidad o fundamento"
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

      {errorFecha ? (
        <EmptyState
          title="No fue posible cargar la matriz de autoridad."
          description={
            errorFecha.fieldErrors?.fecha?.[0] ??
            "La fecha seleccionada no pertenece al ejercicio."
          }
        />
      ) : (
        <section aria-label="Matriz de autoridad">{contenidoMatriz}</section>
      )}

      {detalleCargoId ? (
        <section
          aria-labelledby="detalle-cargo-titulo"
          className="mt-8 border-t border-border-default pt-6"
        >
          {consultaDetalle.isLoading ? (
            <LoadingState label="Cargando el detalle…" />
          ) : consultaDetalle.isError ? (
            <ErrorState
              message="No fue posible cargar el detalle."
              onRetry={() => void consultaDetalle.refetch()}
            />
          ) : detalle ? (
            <>
              <div className="mb-4 flex items-start justify-between gap-4">
                <h2
                  id="detalle-cargo-titulo"
                  className="text-lg font-semibold text-text-900"
                >
                  Detalle de {detalle.cargo.codigo} ·{" "}
                  {detalle.cargo.denominacion}
                </h2>
                <Button
                  variant="ghost"
                  onClick={() => cambiarParametros({ detalle: "" })}
                  aria-label="Cerrar el detalle"
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                  Cerrar el detalle
                </Button>
              </div>

              <dl className="mb-6 grid gap-4 sm:grid-cols-2">
                <div>
                  <dt className="text-sm font-medium text-text-600">Unidad</dt>
                  <dd className="text-text-900">
                    {detalle.cargo.ruta_unidad
                      ? `${detalle.cargo.ruta_unidad} · `
                      : ""}
                    {detalle.cargo.unidad_denominacion ??
                      detalle.cargo.unidad_codigo ??
                      "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-text-600">Estado</dt>
                  <dd className="text-text-900">
                    {ETIQUETA_ESTADO_CARGO[detalle.cargo.estado]}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-text-600">
                    Vigencia
                  </dt>
                  <dd className="text-text-900">
                    {detalle.cargo.vigente_hasta
                      ? `${formatearFechaDeNegocio(
                          detalle.cargo.vigente_desde,
                        )} – ${formatearFechaDeNegocio(
                          detalle.cargo.vigente_hasta,
                        )}`
                      : `Desde ${formatearFechaDeNegocio(
                          detalle.cargo.vigente_desde,
                        )}`}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-text-600">
                    Acto soporte
                  </dt>
                  <dd className="text-text-900">
                    {detalle.acto_soporte.length > 0 ? (
                      <ul className="list-disc pl-5">
                        {detalle.acto_soporte.map((acto) => (
                          <li key={acto.documento_id}>{acto.titulo}</li>
                        ))}
                      </ul>
                    ) : (
                      "Sin documento"
                    )}
                  </dd>
                </div>
              </dl>

              <h3 className="mb-2 text-base font-semibold text-text-900">
                Historial
              </h3>
              <div
                className="relative overflow-x-auto"
                tabIndex={0}
                role="region"
                aria-label={`Historial del cargo ${detalle.cargo.codigo}`}
              >
                <table className="w-full min-w-[720px] border-collapse text-sm">
                  <caption className="sr-only">Historial del cargo</caption>
                  <thead>
                    <tr className="border-b border-border-default text-left text-text-600">
                      <th scope="col" className="px-3 py-2 font-medium">
                        Versión
                      </th>
                      <th scope="col" className="px-3 py-2 font-medium">
                        Estado
                      </th>
                      <th scope="col" className="px-3 py-2 font-medium">
                        Registrada el
                      </th>
                      <th scope="col" className="px-3 py-2 font-medium">
                        Motivo
                      </th>
                      <th scope="col" className="px-3 py-2 font-medium">
                        Competencias
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {detalle.versiones.map((version) => (
                      <tr
                        key={version.version}
                        className="border-b border-border-subtle align-top"
                      >
                        <td className="px-3 py-2 text-text-900">
                          {version.version}
                          {version.version === versionUsada ? (
                            <span className="ml-2 text-xs text-text-600">
                              Usada para esta fecha
                            </span>
                          ) : null}
                        </td>
                        <td className="px-3 py-2 text-text-700">
                          {ETIQUETA_ESTADO_CARGO[version.estado]}
                        </td>
                        <td className="px-3 py-2 text-text-700">
                          {formatearFecha(version.creado_en)}
                        </td>
                        <td className="px-3 py-2 text-text-700">
                          {version.motivo || "—"}
                        </td>
                        <td className="px-3 py-2 text-text-700">
                          {version.competencias.length > 0 ? (
                            version.competencias
                              .map(
                                (competencia) =>
                                  `${ETIQUETA_ACCION[competencia.accion]} · ${
                                    ETIQUETA_MATERIA[competencia.materia]
                                  }: ${describirLimite(competencia)}`,
                              )
                              .join(" / ")
                          ) : (
                            "—"
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {puedeAbrirCargo ? (
                <div className="mt-4">
                  <Link
                    to={`/gobierno/cargos/${ejercicioEfectivo}/${detalleCargoId}`}
                    className="font-medium text-brand-700 underline"
                  >
                    Abrir el cargo
                  </Link>
                </div>
              ) : null}
            </>
          ) : null}
        </section>
      ) : null}
    </PageContent>
  );
}
