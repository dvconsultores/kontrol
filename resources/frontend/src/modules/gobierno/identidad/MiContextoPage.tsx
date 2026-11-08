import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { keepPreviousData } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_IDENTIDAD,
  consultaDeFecha,
  ETIQUETAS_SITUACION_VINCULO,
  ETIQUETAS_CATEGORIA_SEPARACION,
  ETIQUETAS_MOTIVO_SIN_AUTORIDAD,
} from "@/modules/gobierno/api";
import type {
  ContextoInstitucional,
  OcupacionInstitucional,
} from "@/modules/gobierno/api";

function etiquetaCategoria(categoria: string): string {
  return (
    (ETIQUETAS_CATEGORIA_SEPARACION as Record<string, string>)[categoria] ?? categoria
  );
}

export function MiContextoPage() {
  const { activeCompanyId } = useCompany();
  const [fecha, setFecha] = useState<string>("");

  const contextoQuery = useQuery<ContextoInstitucional, ApiError>({
    queryKey: [...CONSULTA_IDENTIDAD, activeCompanyId, "mi-contexto", fecha],
    queryFn: () =>
      apiFetch<ContextoInstitucional>(
        `/gobierno/identidad/mi-contexto${consultaDeFecha(fecha)}`
      ),
    enabled: Boolean(activeCompanyId),
    placeholderData: keepPreviousData,
  });

  if (!activeCompanyId) {
    return (
      <PageContent>
        <div className="text-center text-sm text-text-700">
          Sin empresa seleccionada
        </div>
      </PageContent>
    );
  }

  if (contextoQuery.isLoading && !contextoQuery.data) {
    return (
      <PageContent>
        <LoadingState label="Cargando contexto institucional…" />
      </PageContent>
    );
  }

  if (contextoQuery.isError) {
    return (
      <PageContent>
        <ErrorDeCarga message="No se pudo cargar el contexto institucional." />
      </PageContent>
    );
  }

  const contexto = contextoQuery.data;

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Identidad institucional", to: "/gobierno/identidad" },
        ]}
        title="Mi contexto institucional"
        description="Su cuenta, el funcionario al que corresponde y la autoridad que deriva de su ocupación a la fecha consultada."
      />
      <div className="mt-4 mb-6 max-w-xs">
        <label
          htmlFor="fecha-consulta"
          className="block text-sm font-medium text-text-700"
        >
          Consultar a la fecha
        </label>
        <input
          id="fecha-consulta"
          type="date"
          className="mt-1 block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
          value={fecha}
          onChange={(event) => setFecha(event.target.value)}
        />
      </div>
      {contexto ? (
          <>
            <section aria-labelledby="datos-cuenta-vinculo" className="mb-8">
              <h2
                id="datos-cuenta-vinculo"
                className="mb-4 text-lg font-semibold text-text-900"
              >
                Cuenta y vínculo
              </h2>
              <dl className="grid gap-4 sm:grid-cols-2">
                <div>
                  <dt className="text-sm font-medium text-text-700">Usuario</dt>
                  <dd className="mt-1 text-text-900">
                    {contexto.cuenta.usuario}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-text-700">Estado</dt>
                  <dd className="mt-1 text-text-900">
                    {contexto.cuenta.estado === "ACTIVE" ? "Activa" : "Inactiva"}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-text-700">Vínculo</dt>
                  <dd className="mt-1 text-text-900">
                    {contexto.vinculo ? (
                      <>
                        {contexto.vinculo.codigo}
                        <span className="block text-sm text-text-500">
                          {ETIQUETAS_SITUACION_VINCULO[
                            contexto.vinculo.situacion
                          ] ?? contexto.vinculo.situacion}
                        </span>
                      </>
                    ) : (
                      "Sin vínculo institucional vigente"
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-text-700">Funcionario</dt>
                  <dd className="mt-1 text-text-900">
                    {contexto.funcionario
                      ? `${contexto.funcionario.nombre} · ${contexto.funcionario.documento}`
                      : "—"}
                  </dd>
                </div>
              </dl>
            </section>

            {contexto.es_historica ? (
              <div
                role="alert"
                className="mb-8 rounded-lg border border-warning-300 bg-warning-50 p-4 text-sm text-warning-900"
              >
                La fecha consultada es pasada. Los datos corresponden al contexto
                institucional vigente a esa fecha.
              </div>
            ) : null}

            {contexto ? (
              <section
                aria-labelledby="contexto-institucional"
                className="mb-8"
              >
                <h2
                  id="contexto-institucional"
                  className="mb-4 text-lg font-semibold text-text-900"
                >
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
                          ? (ETIQUETAS_MOTIVO_SIN_AUTORIDAD as Record<string, string>)[
                              contexto.motivo_sin_autoridad
                            ] ?? contexto.motivo_sin_autoridad
                          : "Sin autoridad"}
                    </dd>
                  </div>
                </dl>

                <h3 className="mt-6 mb-3 text-base font-semibold text-text-900">
                  Ocupaciones
                </h3>
                {contexto.ocupaciones.length === 0 ? (
                  <p className="text-sm text-text-700">
                    Sin ocupaciones vigentes en esa fecha
                  </p>
                ) : (
                  <div
                    className="relative overflow-x-auto"
                    tabIndex={0}
                    role="region"
                    aria-label="Tabla de ocupaciones del contexto institucional"
                  >
                    <table className="w-full border-collapse text-left">
                      <caption className="sr-only">
                        Ocupaciones vigentes en la fecha de consulta
                      </caption>
                      <thead>
                        <tr className="border-b border-border-subtle">
                          <th
                            scope="col"
                            className="px-3 py-2 text-sm font-medium text-text-700"
                          >
                            Cargo
                          </th>
                          <th
                            scope="col"
                            className="px-3 py-2 text-sm font-medium text-text-700"
                          >
                            Unidad
                          </th>
                          <th
                            scope="col"
                            className="px-3 py-2 text-sm font-medium text-text-700"
                          >
                            Figura
                          </th>
                          <th
                            scope="col"
                            className="px-3 py-2 text-sm font-medium text-text-700"
                          >
                            Ejerce
                          </th>
                          <th
                            scope="col"
                            className="px-3 py-2 text-sm font-medium text-text-700"
                          >
                            Vigencia
                          </th>
                          <th
                            scope="col"
                            className="px-3 py-2 text-sm font-medium text-text-700"
                          >
                            Autoridad
                          </th>
                          <th
                            scope="col"
                            className="px-3 py-2 text-sm font-medium text-text-700"
                          >
                            Avocaciones
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {contexto.ocupaciones.map(
                          (o: OcupacionInstitucional, indice: number) => (
                            <tr
                              key={`${o.codigo}-${indice}`}
                              className="border-b border-border-subtle"
                            >
                              <td className="px-3 py-2 text-sm text-text-900">
                                {o.cargo}
                                {o.cargo_codigo ? (
                                  <span className="block text-sm text-text-500">
                                    {o.cargo_codigo}
                                  </span>
                                ) : null}
                              </td>
                              <td className="px-3 py-2 text-sm text-text-900">
                                {o.unidad}
                              </td>
                              <td className="px-3 py-2 text-sm text-text-900">
                                {o.figura_etiqueta}
                              </td>
                              <td className="px-3 py-2 text-sm text-text-900">
                                {o.ejerce ? "Sí" : "No"}
                              </td>
                              <td className="px-3 py-2 text-sm text-text-900">
                                {formatearFechaDeNegocio(o.desde)} —{" "}
                                {o.hasta
                                  ? formatearFechaDeNegocio(o.hasta)
                                  : "—"}
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
                              <td className="px-3 py-2 text-sm text-text-900">
                                {o.avocaciones}
                              </td>
                            </tr>
                          )
                        )}
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
                        {rol.nombre}{" "}
                        <span className="text-text-500">({rol.codigo})</span>
                      </li>
                    ))}
                  </ul>
                )}

                <h3 className="mt-6 mb-3 text-base font-semibold text-text-900">
                  Categorías de separación
                </h3>
                {contexto.categorias.length === 0 ? (
                  <p className="text-sm text-text-700">
                    Sin categorías de separación
                  </p>
                ) : (
                  <ul className="list-disc pl-5 text-sm text-text-900">
                    {contexto.categorias.map((categoria) => (
                      <li key={categoria}>{etiquetaCategoria(categoria)}</li>
                    ))}
                  </ul>
                )}

                <h3 className="mt-6 mb-3 text-base font-semibold text-text-900">
                  Conflictos de separación de funciones
                </h3>
                {contexto.conflictos.length === 0 ? (
                  <p className="text-sm text-text-700">
                    Sin conflictos de separación
                  </p>
                ) : (
                  <div
                    role="alert"
                    className="rounded-lg border border-danger-300 bg-danger-50 p-4"
                  >
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
        </>
      ) : null}
    </PageContent>
  );
}


