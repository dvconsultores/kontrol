import { useParams, useSearchParams, Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import { LoadingState } from "@/components/LoadingState";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import {
  formatearFechaDeNegocio,
  hoyDeNegocio,
} from "@/lib/fecha-de-negocio";
import {
  CONSULTA_OCUPACION,
  ETIQUETAS_SITUACION_ASIGNACION,
} from "@/modules/gobierno/api";
import type {
  CargoOcupacion,
  AsignacionResumen,
  CompetenciaOcupacion,
} from "@/modules/gobierno/api";

export function CargoOcupacionPage() {
  const { cargoId } = useParams<{ cargoId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();

  const fecha = searchParams.get("fecha") ?? hoyDeNegocio();
  const puedeVer = tiene("gobierno_ocupacion:view", "empresa");
  const puedeGestionar = tiene("gobierno_ocupacion:manage", "empresa");

  const consultaCargo = useQuery({
    queryKey: [...CONSULTA_OCUPACION, "cargo", activeCompanyId, cargoId, fecha],
    queryFn: () =>
      apiFetch<CargoOcupacion>(
        `/gobierno/ocupacion/cargos/${cargoId}?fecha=${fecha}`,
      ),
    enabled: puedeVer && Boolean(activeCompanyId) && Boolean(cargoId),
    retry: false,
  });

  const cabecera = (
    <PageHeader
      crumbs={[
        { label: "Gobierno" },
        { label: "Ocupación de cargos", to: "/gobierno/ocupacion" },
        { label: consultaCargo.data?.cargo.nombre ?? "Cargo" },
      ]}
      title={consultaCargo.data?.cargo.nombre ?? "Cargo"}
      description={
        consultaCargo.data
          ? `${consultaCargo.data.cargo.codigo} · ${consultaCargo.data.cargo.unidad} · Ejercicio ${consultaCargo.data.cargo.ejercicio}`
          : undefined
      }
      actions={
        puedeGestionar ? (
          <Link
            to={`/gobierno/ocupacion/asignaciones/nueva?cargo=${cargoId}`}
            className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
          >
            Nueva asignación
          </Link>
        ) : null
      }
    />
  );

  if (!puedeVer) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver la ocupación de cargos."
        />
      </PageContent>
    );
  }

  if (consultaCargo.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando cargo…" />
      </PageContent>
    );
  }

  if (consultaCargo.isError) {
    const error = consultaCargo.error;
    if (
      error instanceof ApiError &&
      error.status === 403 &&
      error.code === "MODULE_NOT_ENTITLED"
    ) {
      return (
        <PageContent>
          {cabecera}
          <EmptyState
            title="Módulo no habilitado"
            description="El módulo de Gobierno no está habilitado en la licencia."
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
            description="No tiene permiso para ver la ocupación de cargos."
          />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 404) {
      return (
        <PageContent>
          {cabecera}
          <EmptyState title="Cargo no encontrado" description="El cargo solicitado no existe." />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabecera}
        <ErrorDeCarga
          message="No fue posible cargar el cargo."
          onRetry={() => void consultaCargo.refetch()}
        />
      </PageContent>
    );
  }

  const cargo = consultaCargo.data;
  if (!cargo) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState title="Cargo no encontrado" description="El cargo solicitado no existe." />
      </PageContent>
    );
  }

  const cambiarFecha = (nuevaFecha: string) => {
    setSearchParams(
      (previos) => {
        const nuevos = new URLSearchParams(previos);
        if (nuevaFecha) {
          nuevos.set("fecha", nuevaFecha);
        } else {
          nuevos.delete("fecha");
        }
        return nuevos;
      },
      { replace: true },
    );
  };

  const formatearVigencia = (
    desde: string,
    hasta: string | null,
  ): string => {
    if (hasta) {
      return `${formatearFechaDeNegocio(desde)} – ${formatearFechaDeNegocio(hasta)}`;
    }
    return `${formatearFechaDeNegocio(desde)} – sin fecha final`;
  };

  const renderAsignacionDetalle = (
    asignacion: AsignacionResumen | null,
    _etiqueta: string,
  ) => {
    if (!asignacion) {
      return "—";
    }

    return (
      <div>
        <div className="font-medium text-text-900">
          {asignacion.funcionario.nombre}
        </div>
        <div className="text-sm text-text-600">
          {asignacion.figura_etiqueta}
        </div>
        {asignacion.acto ? (
          <>
            <div className="text-sm text-text-600">
              Por acto:{" "}
              <Link
                to={`/gobierno/actos/${asignacion.acto.id}`}
                className="font-medium text-brand-700 underline"
              >
                {asignacion.acto.tipo} · {asignacion.acto.numero}
              </Link>
            </div>
            <div className="text-sm text-text-600">Emitido por: {asignacion.acto.emisor_cargo}</div>
          </>
        ) : null}
        <div className="text-sm text-text-600">
          {formatearVigencia(asignacion.desde, asignacion.fin_efectivo ?? asignacion.hasta)}
        </div>
        <Link
          to={`/gobierno/ocupacion/asignaciones/${asignacion.id}`}
          className="mt-2 inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
        >
          Ver asignación
        </Link>
      </div>
    );
  };

  const renderAsignacionFila = (
    asignacion: AsignacionResumen,
  ) => {
    const fechaFin = asignacion.fin_efectivo ?? asignacion.hasta ?? "—";

    return (
      <tr key={asignacion.id} className="border-b border-border-subtle align-top">
        <td className="px-3 py-2 text-text-900">
          {asignacion.funcionario.nombre}
        </td>
        <td className="px-3 py-2 text-text-900">
          {asignacion.figura_etiqueta}
        </td>
        <td className="px-3 py-2 text-text-900">
          {formatearFechaDeNegocio(asignacion.desde)}
        </td>
        <td className="px-3 py-2 text-text-900">
          {fechaFin === "—"
            ? "—"
            : formatearFechaDeNegocio(fechaFin)}
        </td>
        <td className="px-3 py-2 text-text-900">
          {ETIQUETAS_SITUACION_ASIGNACION[asignacion.situacion] ??
            asignacion.situacion}
        </td>
        <td className="px-3 py-2">
          <Link
            to={`/gobierno/ocupacion/asignaciones/${asignacion.id}`}
            className="font-medium text-brand-700 underline"
          >
            Ver
          </Link>
        </td>
      </tr>
    );
  };

  const renderCompetencia = (competencia: CompetenciaOcupacion) => {
    const limite =
      competencia.tipo_limite === "SIN_LIMITE"
        ? "Sin límite"
        : `${competencia.monto} ${competencia.moneda}`;

    return (
      <tr key={`${competencia.accion}-${competencia.materia}`} className="border-b border-border-subtle align-top">
        <td className="px-3 py-2 text-text-900">
          {competencia.accion}
        </td>
        <td className="px-3 py-2 text-text-900">
          {competencia.materia}
        </td>
        <td className="px-3 py-2 text-text-900">{limite}</td>
      </tr>
    );
  };

  const renderTitular = () => {
    if (cargo.vacante) {
      return (
        <div
          role="status"
          className="rounded-md border border-border-subtle bg-surface-0 p-4 text-sm text-text-700"
        >
          El cargo está vacante a esa fecha.
        </div>
      );
    }

    const titular = cargo.titular;
    const ejerce = cargo.ejerce;

    return (
      <dl className="grid gap-3 rounded-md border border-border-subtle bg-surface-0 p-4 text-sm sm:grid-cols-2">
        <div>
          <dt className="font-medium text-text-600">Titular</dt>
          <dd className="text-text-900">{renderAsignacionDetalle(titular, "Titular")}</dd>
        </div>
        <div>
          <dt className="font-medium text-text-600">Ejerce</dt>
          <dd className="text-text-900">{renderAsignacionDetalle(ejerce, "Ejerce")}</dd>
        </div>
      </dl>
    );
  };

  return (
    <PageContent>
      {cabecera}

      <section aria-labelledby="filtro-fecha" className="mb-8">
        <h2 id="filtro-fecha" className="sr-only">
          Filtrar por fecha
        </h2>
        <div className="max-w-xs">
          <FormField label="Fecha" htmlFor="cargo-fecha">
            <TextInput
              id="cargo-fecha"
              type="date"
              value={fecha}
              onChange={(evento) => cambiarFecha(evento.target.value)}
            />
          </FormField>
        </div>
      </section>

      <section aria-labelledby="ocupacion-fecha-titulo" className="mb-8">
        <h2
          id="ocupacion-fecha-titulo"
          className="mb-4 text-lg font-semibold text-text-900"
        >
          Ocupación a la fecha
        </h2>
        {renderTitular()}
      </section>

      <section aria-labelledby="autoridad-cargo-titulo" className="mb-8">
        <h2
          id="autoridad-cargo-titulo"
          className="mb-4 text-lg font-semibold text-text-900"
        >
          Autoridad del cargo a la fecha
        </h2>
        {cargo.competencias.length === 0 ? (
          <EmptyState
            title="No tiene competencias"
            description="Este cargo no tiene competencias registradas a la fecha."
          />
        ) : (
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de competencias del cargo"
          >
            <table className="w-full min-w-[600px] border-collapse text-sm">
              <caption className="sr-only">
                Competencias del cargo a la fecha
              </caption>
              <thead>
                <tr className="border-b border-border-default text-left text-text-600">
                  <th scope="col" className="px-3 py-2 font-medium">
                    Acción
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Materia
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Límite
                  </th>
                </tr>
              </thead>
              <tbody>
                {cargo.competencias.map(renderCompetencia)}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="delegaciones-vigentes-titulo" className="mb-8">
        <h2
          id="delegaciones-vigentes-titulo"
          className="mb-4 text-lg font-semibold text-text-900"
        >
          Delegaciones vigentes
        </h2>
        {cargo.delegaciones.length === 0 ? (
          <p className="text-sm text-text-600">No hay delegaciones vigentes.</p>
        ) : (
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de delegaciones vigentes"
          >
            <table className="w-full min-w-[600px] border-collapse text-sm">
              <caption className="sr-only">Delegaciones vigentes</caption>
              <thead>
                <tr className="border-b border-border-default text-left text-text-600">
                  <th scope="col" className="px-3 py-2 font-medium">
                    Funcionario
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Figura
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Vigencia
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    <span className="sr-only">Enlace</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {cargo.delegaciones.map((delegacion) => (
                  <tr
                    key={delegacion.id}
                    className="border-b border-border-subtle align-top"
                  >
                    <td className="px-3 py-2 text-text-900">
                      {delegacion.funcionario.nombre}
                    </td>
                    <td className="px-3 py-2 text-text-900">
                      {delegacion.figura_etiqueta}
                    </td>
                    <td className="px-3 py-2 text-text-900">
                      {formatearVigencia(delegacion.desde, delegacion.fin_efectivo ?? delegacion.hasta)}
                    </td>
                    <td className="px-3 py-2">
                      <Link
                        to={`/gobierno/ocupacion/asignaciones/${delegacion.id}`}
                        className="font-medium text-brand-700 underline"
                      >
                        Ver
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="historia-cargo-titulo">
        <h2
          id="historia-cargo-titulo"
          className="mb-4 text-lg font-semibold text-text-900"
        >
          Historia del cargo
        </h2>
        {cargo.historial.length === 0 ? (
          <p className="text-sm text-text-600">No hay historia registrada.</p>
        ) : (
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de historia del cargo"
          >
            <table className="w-full min-w-[700px] border-collapse text-sm">
              <caption className="sr-only">Historia del cargo</caption>
              <thead>
                <tr className="border-b border-border-default text-left text-text-600">
                  <th scope="col" className="px-3 py-2 font-medium">
                    Funcionario
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Figura
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Desde
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Hasta
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Situación
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    <span className="sr-only">Enlace</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {cargo.historial.map(renderAsignacionFila)}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </PageContent>
  );
}
