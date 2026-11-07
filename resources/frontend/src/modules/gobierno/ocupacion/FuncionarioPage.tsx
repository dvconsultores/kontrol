import { useState } from "react";
import { Link, useParams } from "react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import { LoadingState } from "@/components/LoadingState";
import { formatearFecha } from "@/i18n";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_OCUPACION,
  ETIQUETAS_ESTADO_FUNCIONARIO,
  ETIQUETAS_HISTORIA_OCUPACION,
  ETIQUETAS_SITUACION_ASIGNACION,
} from "@/modules/gobierno/api";
import type {
  EstadoFuncionario,
  FuncionarioDetalle,
} from "@/modules/gobierno/api";

export function FuncionarioPage() {
  const { funcionarioId } = useParams<{ funcionarioId: string }>();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const queryClient = useQueryClient();
  const [nombre, setNombre] = useState<string | null>(null);
  const [estado, setEstado] = useState<EstadoFuncionario | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const puedeVer = tiene("gobierno_ocupacion:view", "empresa");
  const puedeGestionar = tiene("gobierno_ocupacion:manage", "empresa");

  const consultaFuncionario = useQuery({
    queryKey: [
      ...CONSULTA_OCUPACION,
      "funcionario",
      activeCompanyId,
      funcionarioId,
    ],
    queryFn: () =>
      apiFetch<FuncionarioDetalle>(
        `/gobierno/ocupacion/funcionarios/${funcionarioId}`,
      ),
    enabled: puedeVer && Boolean(activeCompanyId) && Boolean(funcionarioId),
    retry: false,
  });

  const modificarFuncionario = useMutation({
    mutationFn: (datos: { nombre: string; estado: EstadoFuncionario }) =>
      apiFetch(`/gobierno/ocupacion/funcionarios/${funcionarioId}`, {
        method: "PATCH",
        ifMatch: String(consultaFuncionario.data?.version ?? ""),
        body: datos,
      }),
    onSuccess: async () => {
      setFormError(null);
      setNombre(null);
      setEstado(null);
      await queryClient.invalidateQueries({
        queryKey: [...CONSULTA_OCUPACION, "funcionario", activeCompanyId, funcionarioId],
      });
      await queryClient.invalidateQueries({
        queryKey: [...CONSULTA_OCUPACION, "funcionarios"],
      });
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError) {
        if (
          error.status === 409 &&
          error.code &&
          (error.code === "GOV_OFFICIAL_STALE" || error.code.includes("_STALE"))
        ) {
          setFormError(
            "Otra persona cambió este funcionario. Recargue la página.",
          );
          return;
        }
        if (error.status >= 400 && error.status < 500) {
          setFormError(error.message);
          return;
        }
      }
      setFormError("No fue posible modificar el funcionario.");
    },
  });

  if (!puedeVer) {
    return (
      <PageContent>
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver este funcionario."
        />
      </PageContent>
    );
  }

  if (consultaFuncionario.isLoading) {
    return (
      <PageContent>
        <LoadingState label="Cargando funcionario…" />
      </PageContent>
    );
  }

  if (consultaFuncionario.isError) {
    const error = consultaFuncionario.error;
    if (error instanceof ApiError && error.status === 404) {
      return (
        <PageContent>
          <EmptyState title="Funcionario no encontrado" />
        </PageContent>
      );
    }
    if (
      error instanceof ApiError &&
      error.status === 403 &&
      error.code === "MODULE_NOT_ENTITLED"
    ) {
      return (
        <PageContent>
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
          <EmptyState
            title="Sin acceso"
            description="No tiene permiso para ver este funcionario."
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        <ErrorDeCarga
          message="No fue posible cargar el funcionario."
          onRetry={() => void consultaFuncionario.refetch()}
        />
      </PageContent>
    );
  }

  if (!consultaFuncionario.data) {
    return (
      <PageContent>
        <EmptyState title="Funcionario no encontrado" />
      </PageContent>
    );
  }

  const funcionario = consultaFuncionario.data;

  const manejarModificacion = (evento: React.FormEvent<HTMLFormElement>) => {
    evento.preventDefault();
    setFormError(null);
    modificarFuncionario.mutate({
      nombre: nombre ?? funcionario.nombre,
      estado: estado ?? funcionario.estado,
    });
  };

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Ocupación de cargos" },
          {
            label: "Funcionarios",
            to: "/gobierno/ocupacion/funcionarios",
          },
          { label: funcionario.nombre },
        ]}
        title={funcionario.nombre}
      />

      <section aria-labelledby="datos-funcionario-titulo" className="mb-8">
        <h2
          id="datos-funcionario-titulo"
          className="mb-4 text-lg font-semibold text-text-900"
        >
          Datos
        </h2>
        <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <dt className="text-sm font-medium text-text-600">Código</dt>
            <dd className="text-sm text-text-900">{funcionario.codigo}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">Nombre</dt>
            <dd className="text-sm text-text-900">{funcionario.nombre}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">Documento</dt>
            <dd className="text-sm text-text-900">
              {funcionario.documento}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">Estado</dt>
            <dd className="text-sm text-text-900">
              {ETIQUETAS_ESTADO_FUNCIONARIO[funcionario.estado]}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">Registrado</dt>
            <dd className="text-sm text-text-900">
              {formatearFecha(funcionario.creado_en)}
            </dd>
          </div>
        </dl>
      </section>

      {puedeGestionar ? (
        <section aria-labelledby="modificar-funcionario-titulo" className="mb-8">
          <h2
            id="modificar-funcionario-titulo"
            className="mb-4 text-lg font-semibold text-text-900"
          >
            Modificar
          </h2>
          <form
            onSubmit={manejarModificacion}
            className="grid gap-4 rounded-md border border-border-subtle bg-surface-0 p-4 sm:grid-cols-2"
          >
            <label className="flex flex-col gap-1">
              <span className="text-sm font-medium text-text-700">Nombre</span>
              <input
                type="text"
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                value={nombre ?? funcionario.nombre}
                onChange={(evento) => setNombre(evento.target.value)}
                minLength={3}
                maxLength={200}
                required
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-sm font-medium text-text-700">Estado</span>
              <select
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                value={estado ?? funcionario.estado}
                onChange={(evento) =>
                  setEstado(evento.target.value as EstadoFuncionario)
                }
              >
                <option value="ACTIVO">
                  {ETIQUETAS_ESTADO_FUNCIONARIO.ACTIVO}
                </option>
                <option value="INACTIVO">
                  {ETIQUETAS_ESTADO_FUNCIONARIO.INACTIVO}
                </option>
              </select>
            </label>
            {formError ? (
              <div role="alert" className="text-sm text-danger-600 sm:col-span-2">
                {formError}
              </div>
            ) : null}
            <div className="sm:col-span-2">
              <button
                type="submit"
                className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
                disabled={modificarFuncionario.isPending}
              >
                {modificarFuncionario.isPending
                  ? "Guardando…"
                  : "Guardar cambios"}
              </button>
            </div>
          </form>
        </section>
      ) : null}

      <section aria-labelledby="asignaciones-funcionario-titulo" className="mb-8">
        <h2
          id="asignaciones-funcionario-titulo"
          className="mb-4 text-lg font-semibold text-text-900"
        >
          Asignaciones
        </h2>
        {funcionario.asignaciones.length === 0 ? (
          <EmptyState title="No tiene asignaciones" />
        ) : (
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de asignaciones del funcionario"
          >
            <table className="w-full min-w-[640px] border-collapse text-sm">
              <caption className="sr-only">
                Asignaciones del funcionario
              </caption>
              <thead>
                <tr className="border-b border-border-default text-left text-text-600">
                  <th scope="col" className="px-3 py-2 font-medium">
                    Código
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Cargo
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Figura
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Vigencia
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Situación
                  </th>
                </tr>
              </thead>
              <tbody>
                {funcionario.asignaciones.map((asignacion) => (
                  <tr
                    key={asignacion.id}
                    className="border-b border-border-subtle align-top"
                  >
                    <td className="px-3 py-2">
                      <Link
                        to={`/gobierno/ocupacion/asignaciones/${asignacion.id}`}
                        aria-label={`Abrir la asignación ${asignacion.codigo}`}
                        className="font-medium text-brand-700 underline"
                      >
                        {asignacion.codigo}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-text-900">
                      {asignacion.cargo.nombre}
                    </td>
                    <td className="px-3 py-2 text-text-900">
                      {asignacion.figura}
                    </td>
                    <td className="px-3 py-2 text-text-900">
                      {`${formatearFechaDeNegocio(asignacion.desde)} – ${(asignacion.fin_efectivo ?? asignacion.hasta) ? formatearFechaDeNegocio(asignacion.fin_efectivo ?? asignacion.hasta) : "sin fecha final"}`}
                    </td>
                    <td className="px-3 py-2 text-text-900">
                      {ETIQUETAS_SITUACION_ASIGNACION[asignacion.situacion]}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="historia-funcionario-titulo">
        <h2
          id="historia-funcionario-titulo"
          className="mb-4 text-lg font-semibold text-text-900"
        >
          Historia
        </h2>
        {funcionario.historia.length === 0 ? (
          <EmptyState title="Sin historia" />
        ) : (
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de historia del funcionario"
          >
            <table className="w-full min-w-[480px] border-collapse text-sm">
              <caption className="sr-only">Historia del funcionario</caption>
              <thead>
                <tr className="border-b border-border-default text-left text-text-600">
                  <th scope="col" className="px-3 py-2 font-medium">
                    Evento
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Usuario
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Fecha
                  </th>
                </tr>
              </thead>
              <tbody>
                {funcionario.historia.map((evento) => (
                  <tr
                    key={evento.id}
                    className="border-b border-border-subtle align-top"
                  >
                    <td className="px-3 py-2 text-text-900">
                      {ETIQUETAS_HISTORIA_OCUPACION[evento.tipo] ?? evento.tipo}
                    </td>
                    <td className="px-3 py-2 text-text-900">
                      {evento.actor}
                    </td>
                    <td className="px-3 py-2 text-text-900">
                      {formatearFecha(evento.creado_en)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </PageContent>
  );
}
