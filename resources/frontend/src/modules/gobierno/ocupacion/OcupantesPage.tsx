import { useState } from "react";
import { Link } from "react-router";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
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
import { Button } from "@/components/Button";
import { hoyDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_OCUPACION,
  consultaDeOcupacion,
} from "@/modules/gobierno/api";
import type { OcupacionListado } from "@/modules/gobierno/api";

export function OcupantesPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const [ejercicio, setEjercicio] = useState<number>(
    Number(hoyDeNegocio().slice(0, 4)),
  );
  const [fecha, setFecha] = useState<string>(hoyDeNegocio());
  const [texto, setTexto] = useState<string>("");
  const [pagina, setPagina] = useState<number>(1);

  const puedeVer = tiene("gobierno_ocupacion:view", "empresa");
  const puedeGestionar = tiene("gobierno_ocupacion:manage", "empresa");

  const consultaOcupacion = useQuery({
    queryKey: [
      ...CONSULTA_OCUPACION,
      "cargos",
      activeCompanyId,
      ejercicio,
      fecha,
      texto,
      pagina,
    ],
    queryFn: () =>
      apiFetch<OcupacionListado>(
        `/gobierno/ocupacion/cargos${consultaDeOcupacion({
          ejercicio,
          fecha,
          texto,
          pagina,
        })}`,
      ),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
    placeholderData: keepPreviousData,
  });

  const cabecera = (
    <PageHeader
      crumbs={[
        { label: "Gobierno" },
        { label: "Ocupación de cargos" },
      ]}
      title="Ocupación de cargos"
      description="Quién ejerce cada cargo, bajo qué figura y por qué acto, a la fecha que elija."
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Link
            to="/gobierno/ocupacion/asignaciones"
            className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
          >
            Asignaciones
          </Link>
          <Link
            to="/gobierno/ocupacion/funcionarios"
            className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
          >
            Funcionarios
          </Link>
          {puedeGestionar ? (
            <Link
              to="/gobierno/ocupacion/asignaciones/nueva"
              className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
            >
              Nueva asignación
            </Link>
          ) : null}
        </div>
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

  if (consultaOcupacion.isLoading && !consultaOcupacion.data) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando ocupación…" />
      </PageContent>
    );
  }

  if (consultaOcupacion.isError) {
    const error = consultaOcupacion.error;
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
    return (
      <PageContent>
        {cabecera}
        <ErrorDeCarga
          message="No fue posible cargar la ocupación de cargos."
          onRetry={() => void consultaOcupacion.refetch()}
        />
      </PageContent>
    );
  }

  const datos = consultaOcupacion.data;
  if (!datos) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState title="Aún no hay cargos" description="No hay cargos para mostrar." />
      </PageContent>
    );
  }

  const totalPaginas = Math.max(1, Math.ceil(datos.total / datos.por_pagina));

  const cambiarEjercicio = (valor: string) => {
    const numero = Number(valor);
    setEjercicio(Number.isNaN(numero) ? 0 : numero);
    setPagina(1);
  };

  const cambiarFecha = (valor: string) => {
    setFecha(valor);
    setPagina(1);
  };

  const cambiarTexto = (valor: string) => {
    setTexto(valor);
    setPagina(1);
  };

  return (
    <PageContent>
      {cabecera}

      <form
        role="search"
        aria-label="Filtrar ocupación de cargos"
        className="mb-6"
        onSubmit={(evento) => evento.preventDefault()}
      >
        <div className="grid gap-3 sm:grid-cols-3">
          <FormField label="Ejercicio" htmlFor="ocupacion-ejercicio">
            <TextInput
              id="ocupacion-ejercicio"
              type="number"
              value={String(ejercicio)}
              onChange={(evento) => cambiarEjercicio(evento.target.value)}
            />
          </FormField>
          <FormField label="Fecha" htmlFor="ocupacion-fecha">
            <TextInput
              id="ocupacion-fecha"
              type="date"
              value={fecha}
              onChange={(evento) => cambiarFecha(evento.target.value)}
            />
          </FormField>
          <FormField label="Buscar cargo" htmlFor="ocupacion-texto">
            <TextInput
              id="ocupacion-texto"
              type="text"
              value={texto}
              onChange={(evento) => cambiarTexto(evento.target.value)}
              placeholder="Nombre o código"
            />
          </FormField>
        </div>
      </form>

      {datos.items.length === 0 ? (
        <EmptyState
          title="No hay cargos en ese ejercicio"
          description="Registre cargos en Cargos y competencias o elija otro ejercicio."
        />
      ) : (
        <>
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de ocupación de cargos"
          >
            <table className="w-full min-w-[900px] border-collapse text-sm">
              <caption className="sr-only">
                Ocupación de cargos a la fecha indicada
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
                    Titular
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Ejerce
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Situación
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Delegaciones
                  </th>
                </tr>
              </thead>
              <tbody>
                {datos.items.map((fila) => (
                  <tr
                    key={fila.cargo.id}
                    className="border-b border-border-subtle align-top"
                  >
                    <td className="px-3 py-2">
                      <Link
                        to={`/gobierno/ocupacion/cargos/${fila.cargo.id}?fecha=${fecha}`}
                        className="font-medium text-brand-700 underline"
                      >
                        {fila.cargo.nombre}
                      </Link>
                      <div className="text-xs text-text-600">{fila.cargo.codigo}</div>
                    </td>
                    <td className="px-3 py-2 text-text-900">{fila.cargo.unidad}</td>
                    <td className="px-3 py-2">
                      {fila.titular ? (
                        <>
                          <div>{fila.titular.funcionario.nombre}</div>
                          <div className="text-xs text-text-600">
                            {fila.titular.funcionario.documento}
                          </div>
                        </>
                      ) : (
                        "Sin titular"
                      )}
                    </td>
                    <td className="px-3 py-2">
                      {fila.ejerce ? (
                        <>
                          <div>{fila.ejerce.funcionario.nombre}</div>
                          <div className="text-xs text-text-600">
                            {fila.ejerce.figura_etiqueta}
                          </div>
                        </>
                      ) : (
                        "Nadie"
                      )}
                    </td>
                    <td className="px-3 py-2">
                      {fila.vacante ? "Vacante" : "Cubierto"}
                    </td>
                    <td className="px-3 py-2">{fila.delegaciones}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <div className="text-sm text-text-700">
              Página {pagina} de {totalPaginas}
            </div>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                disabled={pagina <= 1}
                onClick={() => setPagina((actual) => Math.max(1, actual - 1))}
              >
                Anterior
              </Button>
              <Button
                variant="secondary"
                disabled={pagina >= totalPaginas}
                onClick={() =>
                  setPagina((actual) => Math.min(totalPaginas, actual + 1))
                }
              >
                Siguiente
              </Button>
            </div>
          </div>
        </>
      )}
    </PageContent>
  );
}
